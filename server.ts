/**
 * =============================================================================
 *   server.ts — Dummy Express API with Intentional N+1 Bottleneck
 * =============================================================================
 *
 *   This is a demonstration Express server that simulates a real API route
 *   suffering from the N+1 query anti-pattern. The Prisma slow-query
 *   interceptor middleware is active, so when you hit /api/posts, it will:
 *
 *     1. Execute the N+1 loop (deliberately slow)
 *     2. Detect the latency exceeds 500ms
 *     3. Write slow_query_input.json
 *     4. Trigger run_phase_1.py -> run_phase_2.py -> run_phase_3.py
 *
 *   Usage:
 *     npx ts-node server.ts
 *     curl http://localhost:3000/api/posts
 *
 *   Prerequisites:
 *     npm install express @types/express ts-node typescript @prisma/client
 * =============================================================================
 */

import express, { Request, Response } from 'express';
import { PrismaClient } from '@prisma/client';
import { performance } from 'perf_hooks';
import { exec } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

const app = express();
const PORT = process.env.PORT || 3000;

// ---------------------------------------------------------------------------
// Prisma Client with slow-query interception built in
// ---------------------------------------------------------------------------
const basePrisma = new PrismaClient({
  log: [
    { emit: 'stdout', level: 'query' },
    { emit: 'stdout', level: 'warn' },
  ],
});

const SLOW_THRESHOLD_MS = 500;
const ARTIFACTS_DIR = path.join(__dirname, 'optimization_artifacts');

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

          // Build the input payload for Phase 1
          const payload = {
            raw_query: `Prisma ${model}.${operation}(${JSON.stringify(args)})`,
            query_count: 1,
            model: model || 'unknown',
            operation,
            duration_ms: parseFloat(duration.toFixed(2)),
            timestamp: new Date().toISOString(),
            baseline_explain: `Latency ${duration.toFixed(1)}ms detected by Prisma middleware interceptor.`,
            intercepted_code: 'See server.ts /api/posts route — N+1 loop pattern.',
          };

          // Write the payload for the AI agent
          const inputFile = path.join(ARTIFACTS_DIR, 'slow_query_input.json');
          fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
          fs.writeFileSync(inputFile, JSON.stringify(payload, null, 2), 'utf-8');
          console.log(`[INTERCEPTOR] Wrote payload to ${inputFile}`);

          // Trigger the AI pipeline
          const cmd = [
            `python3 ${path.join(ARTIFACTS_DIR, 'run_phase_1.py')}`,
            `python3 ${path.join(ARTIFACTS_DIR, 'run_phase_2.py')}`,
            `python3 ${path.join(ARTIFACTS_DIR, 'run_phase_3.py')}`,
          ].join(' && ');

          console.log(`[INTERCEPTOR] Triggering AI pipeline...`);
          exec(
            cmd,
            { env: { ...process.env, PYTHONIOENCODING: 'utf-8' } },
            (error, stdout, stderr) => {
              if (error) {
                console.error(`[PIPELINE ERROR] ${error.message}`);
                return;
              }
              if (stderr) console.warn(`[PIPELINE STDERR]\n${stderr}`);
              console.log(`[PIPELINE DONE]\n${stdout}`);
            }
          );
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
      '/api/health': 'GET — Health check',
    },
  });
});

app.get('/api/health', (_req: Request, res: Response) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
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

  The Prisma middleware interceptor is ACTIVE.
  Any query >500ms will trigger the AI optimization pipeline.
========================================================
`);
});