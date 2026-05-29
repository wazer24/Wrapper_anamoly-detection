# setup_postgres_portable.ps1
# Portable PostgreSQL 16 - No admin rights required
# Runs entirely inside e:\Ai_Hackathon\pg_portable\

$ErrorActionPreference = "Stop"

$ROOT     = "e:\Ai_Hackathon"
$PG_DIR   = "$ROOT\pg_portable"
$PG_DATA  = "$PG_DIR\data"
$PG_LOG   = "$PG_DIR\pg.log"
$PG_PORT  = 5432
$PG_USER  = "postgres"
$PG_PASS  = "postgres"
$PG_DB    = "postgres"
$ZIP_URL  = "https://sbp.enterprisedb.com/getfile.jsp?fileid=1260202"
$ZIP_PATH = "$ROOT\pg16_binaries.zip"
$BIN      = "$PG_DIR\bin"

function Step($msg)  { Write-Host "`n=[ $msg ]=" -ForegroundColor Cyan   }
function OK($msg)    { Write-Host "  OK  $msg"   -ForegroundColor Green  }
function INFO($msg)  { Write-Host "  ->  $msg"   -ForegroundColor Yellow }
function ERR($msg)   { Write-Host "  ERR $msg"   -ForegroundColor Red    }

# Step 0: Check if already running
Step "0: Checking port $PG_PORT"
$listening = netstat -an 2>$null | Select-String ":$PG_PORT "
if ($listening -match "LISTENING") {
    OK "Port $PG_PORT already has a listener."
    $env:PATH = "$BIN;$env:PATH"
    $env:PGPASSWORD = $PG_PASS
} else {

    # Step 1: Download
    Step "1: Download PostgreSQL 16.14 Windows x64 binaries (~350 MB)"
    if (Test-Path "$BIN\pg_ctl.exe") {
        OK "Binaries already present at $BIN"
    } else {
        if (-not (Test-Path $ZIP_PATH)) {
            INFO "Downloading from EDB..."
            $wc = New-Object System.Net.WebClient
            $wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            $wc.DownloadFile($ZIP_URL, $ZIP_PATH)
            OK "Downloaded to $ZIP_PATH"
        } else {
            OK "Zip already at $ZIP_PATH - skipping download"
        }

        # Step 2: Extract
        Step "2: Extracting to $PG_DIR"
        if (-not (Test-Path $PG_DIR)) { New-Item -ItemType Directory -Path $PG_DIR | Out-Null }
        $tmp = "$ROOT\_pg_tmp"
        INFO "Expanding archive (1-2 min)..."
        Expand-Archive -Path $ZIP_PATH -DestinationPath $tmp -Force
        $inner = Get-ChildItem $tmp | Select-Object -First 1
        if (Test-Path $PG_DIR) { Remove-Item $PG_DIR -Recurse -Force }
        Move-Item -Path $inner.FullName -Destination $PG_DIR -Force
        Remove-Item $tmp      -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item $ZIP_PATH -Force         -ErrorAction SilentlyContinue
        OK "Extracted to $PG_DIR"
    }

    $env:PATH = "$BIN;$env:PATH"
    $env:PGPASSWORD = $PG_PASS

    # Step 3: initdb
    Step "3: Initializing data cluster"
    if (Test-Path "$PG_DATA\PG_VERSION") {
        OK "Cluster already initialized at $PG_DATA"
    } else {
        INFO "Running initdb..."
        & "$BIN\initdb.exe" --pgdata="$PG_DATA" --username="$PG_USER" --encoding=UTF8 --locale=C --auth=trust
        if ($LASTEXITCODE -ne 0) { ERR "initdb failed"; exit 1 }

        $hba = @"
# TYPE  DATABASE  USER  ADDRESS         METHOD
local   all       all                   trust
host    all       all   127.0.0.1/32    trust
host    all       all   ::1/128         trust
"@
        Set-Content "$PG_DATA\pg_hba.conf" -Value $hba -Encoding UTF8
        OK "Cluster initialized with trust auth"
    }

    # Step 4: Start server
    Step "4: Starting PostgreSQL server"
    $st = & "$BIN\pg_ctl.exe" status -D "$PG_DATA" 2>&1
    if ($st -match "server is running") {
        OK "Already running"
    } else {
        INFO "Starting..."
        & "$BIN\pg_ctl.exe" start -D "$PG_DATA" -l "$PG_LOG" -o "-p $PG_PORT -h 127.0.0.1"
        Start-Sleep -Seconds 5
        $st2 = & "$BIN\pg_ctl.exe" status -D "$PG_DATA" 2>&1
        if ($st2 -notmatch "server is running") {
            ERR "Server did not start. Log:"
            if (Test-Path $PG_LOG) { Get-Content $PG_LOG -Tail 20 }
            exit 1
        }
        OK "Server started. Log: $PG_LOG"
    }
}

# Step 5: Wait for connections
Step "5: Waiting for PostgreSQL to accept connections"
$ready = $false
for ($i = 1; $i -le 15; $i++) {
    $r = & "$BIN\pg_isready.exe" -h 127.0.0.1 -p $PG_PORT -U $PG_USER 2>&1
    if ($r -match "accepting connections") { OK "Ready!"; $ready = $true; break }
    INFO "[$i/15] $r - waiting 2s..."
    Start-Sleep -Seconds 2
}
if (-not $ready) { ERR "Server not ready after 30s"; exit 1 }

# Step 6: Install HypoPG stub
Step "6: Installing HypoPG stub extension"
$hypoCount = & "$BIN\psql.exe" -h 127.0.0.1 -p $PG_PORT -U $PG_USER -d $PG_DB `
    -tAc "SELECT count(*) FROM pg_available_extensions WHERE name = 'hypopg';" 2>&1

if ($hypoCount.Trim() -eq "1") {
    OK "HypoPG already registered"
} else {
    $ctrlFile = "$PG_DIR\share\extension\hypopg.control"
    $sqlFile  = "$PG_DIR\share\extension\hypopg--1.4.1.sql"

    Set-Content -Path $ctrlFile -Encoding UTF8 -Value @"
default_version = '1.4.1'
comment = 'Hypothetical indexes - stub for demo'
"@

    # Write SQL stub - uses dollar-quoting correctly
    $stubSql = "-- HypoPG stub extension for demo/simulation`n"
    $stubSql += "CREATE OR REPLACE FUNCTION hypopg_create_index(index_definition text)`n"
    $stubSql += "RETURNS TABLE(indexrelid oid, indexname text)`n"
    $stubSql += "LANGUAGE plpgsql AS `$func`$`n"
    $stubSql += "DECLARE v_oid oid;`n"
    $stubSql += "BEGIN`n"
    $stubSql += "  SELECT (max(oid) + (random()*1000)::int)::oid INTO v_oid FROM pg_class;`n"
    $stubSql += "  indexrelid := v_oid;`n"
    $stubSql += "  indexname  := 'hypothetical_' || substr(md5(index_definition), 1, 12);`n"
    $stubSql += "  RETURN NEXT;`n"
    $stubSql += "END;`n"
    $stubSql += "`$func`$;`n`n"
    $stubSql += "CREATE OR REPLACE FUNCTION hypopg_drop_index(indexrelid oid)`n"
    $stubSql += "RETURNS boolean LANGUAGE sql AS `$`$ SELECT true; `$`$;`n`n"
    $stubSql += "CREATE OR REPLACE FUNCTION hypopg_reset()`n"
    $stubSql += "RETURNS void LANGUAGE sql AS `$`$ SELECT; `$`$;`n"

    Set-Content -Path $sqlFile -Encoding UTF8 -Value $stubSql
    OK "HypoPG stub files written"
}

& "$BIN\psql.exe" -h 127.0.0.1 -p $PG_PORT -U $PG_USER -d $PG_DB `
    -c "CREATE EXTENSION IF NOT EXISTS hypopg;" 2>&1 | Write-Host
OK "HypoPG extension active"

# Step 7: Seed demo schema
Step "7: Seeding demo schema"
$seedFile = "$ROOT\_seed.sql"

$seed = "DROP TABLE IF EXISTS order_items CASCADE;`n"
$seed += "DROP TABLE IF EXISTS orders CASCADE;`n"
$seed += "DROP TABLE IF EXISTS customers CASCADE;`n`n"
$seed += "CREATE TABLE customers (customer_id SERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL, full_name VARCHAR(255), created_at TIMESTAMPTZ DEFAULT NOW());`n"
$seed += "CREATE TABLE orders (order_id SERIAL PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id), status VARCHAR(50) NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ);`n"
$seed += "CREATE INDEX idx_orders_cust ON orders (customer_id);`n"
$seed += "CREATE TABLE order_items (item_id SERIAL PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(order_id), product_id INTEGER NOT NULL, quantity INTEGER NOT NULL, unit_price NUMERIC(10,2) NOT NULL);`n`n"
$seed += "INSERT INTO customers (email, full_name) SELECT 'user_'||gs||'@example.com','User '||gs FROM generate_series(1,5000) gs;`n"
$seed += "INSERT INTO orders (customer_id, status, created_at) SELECT (random()*4999+1)::int, (ARRAY['completed','shipped','pending','cancelled','processing'])[floor(random()*5+1)], NOW()-(random()*400)::int*INTERVAL'1 day' FROM generate_series(1,80000) gs;`n"
$seed += "INSERT INTO order_items (order_id, product_id, quantity, unit_price) SELECT (random()*79999+1)::int,(random()*999+1)::int,(random()*9+1)::int, round((random()*499+0.99)::numeric,2) FROM generate_series(1,300000) gs;`n`n"
$seed += "ANALYZE customers, orders, order_items;`n"
$seed += "SELECT 'customers' AS tbl, count(*) AS rows FROM customers UNION ALL SELECT 'orders', count(*) FROM orders UNION ALL SELECT 'order_items', count(*) FROM order_items;`n"

Set-Content -Path $seedFile -Encoding UTF8 -Value $seed
INFO "Inserting 385,000 rows (30-60 sec)..."
& "$BIN\psql.exe" -h 127.0.0.1 -p $PG_PORT -U $PG_USER -d $PG_DB -f $seedFile 2>&1 | Write-Host
Remove-Item $seedFile -Force -ErrorAction SilentlyContinue
OK "Demo data seeded"

# Step 8: Final check
Step "8: Final verification"
& "$BIN\psql.exe" -h 127.0.0.1 -p $PG_PORT -U $PG_USER -d $PG_DB -c "SELECT version();" 2>&1 | Write-Host
& "$BIN\psql.exe" -h 127.0.0.1 -p $PG_PORT -U $PG_USER -d $PG_DB -c "SELECT hypopg_reset();" 2>&1 | Write-Host

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE - Run Phase 2 now:" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  & 'e:/Ai_Hackathon/.venv/Scripts/python.exe' ``" -ForegroundColor Cyan
Write-Host "      'e:/Ai_Hackathon/optimization_artifacts/run_phase_2.py' ``" -ForegroundColor Cyan
Write-Host "      --host 127.0.0.1 --port 5432 --dbname postgres --user postgres --password postgres" -ForegroundColor Cyan
Write-Host ""
Write-Host "  To stop server later:" -ForegroundColor Yellow
Write-Host "  & '$BIN\pg_ctl.exe' stop -D '$PG_DATA'" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Green
