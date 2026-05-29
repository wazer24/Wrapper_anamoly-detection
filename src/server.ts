/**
 * =============================================================================
 *   server.ts — Express API with Intentional N+1 Bottleneck + HITL Approval
 * =============================================================================
 *
 *   This is a demonstration Express server that simulates a real API route
 *   suffering from the N+1 query anti-pattern. The Prisma slow-query
 *   interceptor middleware is active, so when you hit /api/posts, it will:
 *
 *     1. Execute the N+1 loop (deliberately slow)
 *     2. Detect the latency exceeds 500ms
 *     3. Queue the slow query event to Redis for the agent worker
 *
 *   Also exposes approval endpoints for human-in-the-loop (Phase 5).
 *
 *   Usage:
 *     npx ts-node server.ts
 *     curl http://localhost:3000/api/posts
 *     curl -X POST http://localhost:3000/api/approve/0 -H "Content-Type: application/json" -d '{"status":"APPROVED"}'
 *
 *   Prerequisites:
 *     npm install express @types/express ts-node typescript @prisma/client
 * =============================================================================
 */

import express, { Request, Response } from 'express';
import { PrismaClient } from '@prisma/client';
import { performance } from 'perf_hooks';
import { createClient } from 'redis';
import * as fs from 'fs';
import * as path from 'path';

const app = express();
app.use(express.json());
const PORT = process.env.PORT || 3000;

// Initialize Redis Client for event streaming
const redisClient = createClient({ url: process.env.REDIS_URL || 'redis://localhost:6379' });
redisClient.on('error', (err) => console.error('[REDIS ERROR]', err));
redisClient.connect().catch(console.error);

// ---------------------------------------------------------------------------
// Prisma Client with slow-query interception built in
// ---------------------------------------------------------------------------
const basePrisma = new PrismaClient({
  log: [
    { emit: 'stdout', level: 'query' },
    { emit: 'stdout', level: 'warn' },
  ],
});

const SLOW_THRESHOLD_MS = 1;
const ARTIFACTS_DIR = path.join(__dirname, '..', 'optimization_artifacts');

/**
 * Extended Prisma client that intercepts every operation,
 * measures its latency, and triggers the AI pipeline if slow.
 */
const prisma = basePrisma.$extends({
  query: {
    $allOperations({ model, operation, args, query }) {
      const start = performance.now();

      return query(args).then((result) => {
        const duration = performance.now() - start;

        if (duration > SLOW_THRESHOLD_MS) {
          console.warn(
            `\n[SLOW QUERY] Model: ${model || 'raw'} | Op: ${operation} | ${duration.toFixed(1)}ms`
          );

          const rowsReturned = Array.isArray(result) ? result.length : (result ? 1 : 0);
          const payloadSizeKb = parseFloat((Buffer.byteLength(JSON.stringify(result || {})) / 1024).toFixed(2));

          // Build the input payload for Phase 1
          const payload = {
            raw_query: `Prisma ${model}.${operation}(${JSON.stringify(args)})`,
            query_count: 1,
            model: model || 'unknown',
            operation,
            duration_ms: parseFloat(duration.toFixed(2)),
            rows_returned: rowsReturned,
            rows_scanned: null,
            payload_size_kb: payloadSizeKb,
            timestamp: new Date().toISOString(),
            baseline_explain: `Latency ${duration.toFixed(1)}ms detected by Prisma middleware interceptor.`,
            intercepted_code: 'See server.ts — N+1 loop pattern.',
          };

          // ---------------------------------------------------------
          // PHASE 1 UPGRADE: Event-Driven Ingestion via Redis Streams
          // ---------------------------------------------------------
          const tenantId = process.env.TENANT_ID || 'default_tenant';
          const streamPayload = {
            query_text: payload.raw_query,
            params: JSON.stringify(args),
            duration_ms: payload.duration_ms.toString(),
            tenant_id: tenantId,
            full_payload: JSON.stringify(payload) // Preserve full context for Agent Worker
          };

          redisClient.xAdd('slow_queries', '*', streamPayload)
            .then((messageId) => {
              console.log(\`[INTERCEPTOR] Queued slow query event to Redis stream 'slow_queries' (ID: \${messageId})\`);
            })
            .catch((err) => {
              console.error(\`[INTERCEPTOR ERROR] Failed to queue event to Redis: \${err.message}\`);
            });
        }

        return result;
      });
    },
  },
});


// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------
app.get('/', (_req: Request, res: Response) => {
  res.json({
    status: 'ok',
    message: 'AI Database Optimization Demo Server',
    endpoints: {
      '/api/posts': 'GET — Triggers N+1 bottleneck (slow, for testing)',
      '/api/posts/optimized': 'GET — Uses Prisma include (fast, fixed)',
      '/api/customers': 'GET — Missing index (full table scan)',
      '/api/approve/:requestId': 'POST — Approve or deny a fix (HITL)',
      '/api/approval/:requestId': 'GET — Check approval request status',
      '/api/health': 'GET — Health check',
    },
  });
});

app.get('/api/health', (_req: Request, res: Response) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

/**
 * MISSING INDEX ANTI-PATTERN ROUTE
 *
 * Searches by 'email', which is not indexed in the Prisma schema.
 * As the table grows, this causes a Full Table Scan.
 */
app.get('/api/customers', async (req: Request, res: Response) => {
  try {
    const startTime = performance.now();
    
    // Step 1: Query by a column with no index
    const emailToSearch = req.query.email || 'user5@test.com';
    const customer = await (prisma as any).customer.findFirst({
      where: { email: emailToSearch },
    });

    const totalTime = performance.now() - startTime;

    res.json({
      route: '/api/customers',
      pattern: 'MISSING INDEX (Full Table Scan)',
      query_count: 1,
      total_latency_ms: parseFloat(totalTime.toFixed(2)),
      data: customer,
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * N+1 ANTI-PATTERN ROUTE (intentionally slow)
 *
 * Fetches all pending orders, then loops to fetch each customer
 * individually. This triggers the Prisma middleware interceptor.
 */
app.get('/api/posts', async (_req: Request, res: Response) => {
  try {
    const startTime = performance.now();

    // Step 1: Fetch all orders (1 query)
    const orders = await (prisma as any).order.findMany({
      where: { status: 'pending' },
    });

    // Step 2: N+1 loop — fetch each customer individually (N queries)
    const enrichedOrders = [];
    for (const order of orders) {
      const customer = await (prisma as any).customer.findUnique({
        where: { customerId: order.customerId },
      });
      enrichedOrders.push({ ...order, customer });
    }

    const totalTime = performance.now() - startTime;

    res.json({
      route: '/api/posts',
      pattern: 'N+1 ANTI-PATTERN (intentionally slow)',
      query_count: 1 + orders.length,
      total_latency_ms: parseFloat(totalTime.toFixed(2)),
      result_count: enrichedOrders.length,
      data: enrichedOrders.slice(0, 5), // Return first 5 for brevity
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * OPTIMIZED ROUTE (the fix the AI would recommend)
 *
 * Uses Prisma `include` to fetch orders + customers in a single JOIN.
 */
app.get('/api/posts/optimized', async (_req: Request, res: Response) => {
  try {
    const startTime = performance.now();

    const orders = await (prisma as any).order.findMany({
      where: { status: 'pending' },
      include: { customer: true },
    });

    const totalTime = performance.now() - startTime;

    res.json({
      route: '/api/posts/optimized',
      pattern: 'EAGER LOADING (single JOIN — AI-recommended fix)',
      query_count: 1,
      total_latency_ms: parseFloat(totalTime.toFixed(2)),
      result_count: orders.length,
      data: orders.slice(0, 5),
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});


// ---------------------------------------------------------------------------
// HITL Approval Endpoints (Phase 5)
// ---------------------------------------------------------------------------

/**
 * POST /api/approve/:requestId
 *
 * Sets the approval status for a pending approval request.
 * The agent worker polls this status to resume the interrupted LangGraph.
 *
 * Body: { "status": "APPROVED" | "DENIED" }
 */
app.post('/api/approve/:requestId', async (req: Request, res: Response) => {
  try {
    const requestId = parseInt(req.params.requestId, 10);
    if (isNaN(requestId)) {
      res.status(400).json({ status: 'error', message: 'Invalid requestId' });
      return;
    }

    const { status } = req.body;
    if (status !== 'APPROVED' && status !== 'DENIED') {
      res.status(400).json({ status: 'error', message: "Status must be 'APPROVED' or 'DENIED'" });
      return;
    }

    // Use Temporal signal if workflow ID is known; otherwise fall back to in-memory
    const workflowId = `optimize-${process.env.TENANT_ID || 'default'}-${requestId}`;
    const temporalHost = process.env.TEMPORAL_HOST || 'localhost:7233';

    try {
      const { Client } = await import('@temporalio/client');
      const temporalClient = new Client({ identity: 'server-ts' });
      const handle = temporalClient.workflow.getHandle(workflowId);
      await handle.signal('approve_signal', status === 'APPROVED');
      console.log(`[APPROVAL] Signaled workflow ${workflowId} with ${status}`);
    } catch (signalErr) {
      // Fallback: store approval in Redis for the worker to poll
      try {
        await redisClient.set(`approval:${requestId}`, status);
        console.log(`[APPROVAL] Stored approval ${status} for request ${requestId} in Redis`);
      } catch (redisErr) {
        console.error(`[APPROVAL] Failed to store approval in Redis: ${redisErr}`);
      }
    }

    res.json({ status: 'ok', request_id: requestId, decision: status });
  } catch (error: any) {
    res.status(500).json({ status: 'error', message: error.message });
  }
});

/**
 * GET /api/approval/:requestId
 *
 * Returns the current status of an approval request.
 */
app.get('/api/approval/:requestId', async (req: Request, res: Response) => {
  try {
    const requestId = parseInt(req.params.requestId, 10);
    if (isNaN(requestId)) {
      res.status(400).json({ status: 'error', message: 'Invalid requestId' });
      return;
    }

    const redisStatus = await redisClient.get(`approval:${requestId}`);
    res.json({
      status: redisStatus ? 'ok' : 'pending',
      request_id: requestId,
      decision: redisStatus || 'pending',
    });
  } catch (error: any) {
    res.status(500).json({ status: 'error', message: error.message });
  }
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
app.listen(PORT, () => {
  console.log(`
========================================================
  AI DB Optimizer Demo Server
  http://localhost:${PORT}
========================================================
  
  Endpoints:
    GET /                       — API info
    GET /api/health             — Health check
    GET /api/posts              — N+1 bottleneck (triggers AI agent)
    GET /api/posts/optimized    — Fixed version (single JOIN)
    GET /api/customers          — Missing index (full table scan)
    POST /api/approve/:id       — HITL: approve/deny a fix
    GET  /api/approval/:id      — HITL: check approval status

  The Prisma middleware interceptor is ACTIVE.
  Any query >500ms will trigger the AI optimization pipeline.
========================================================
`);
});