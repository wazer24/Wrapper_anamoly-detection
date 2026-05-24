import { Prisma } from '@prisma/client';
import { exec } from 'child_process';
import { performance } from 'perf_hooks';

/**
 * Prisma Client Extension to intercept slow queries (> 500ms)
 * and trigger the Python-based AI Database Optimizer Pipeline.
 */
export const slowQueryInterceptor = Prisma.defineExtension((client) => {
  return client.$extends({
    query: {
      $allOperations({ model, operation, args, query }) {
        const start = performance.now();

        return query(args).finally(() => {
          const duration = performance.now() - start;

          // Threshold: 500ms
          if (duration > 500) {
            console.warn(
              `⚠️ [SLOW QUERY DETECTED] Model: ${model || 'Unknown'}, Operation: ${operation} took ${duration.toFixed(2)}ms`
            );

            // Command to trigger the optimization pipeline sequentially
            const cmd = 'python3 run_phase_1.py && python3 run_phase_2.py && python3 run_phase_3.py';

            // execute the pipeline asynchronously using child_process.exec to prevent blocking the event loop
            exec(cmd, { env: { ...process.env, PYTHONIOENCODING: 'utf-8' } }, (error, stdout, stderr) => {
              if (error) {
                console.error(`[CI/CD Interceptor Error] Optimization pipeline run failed: ${error.message}`);
                return;
              }
              if (stderr) {
                console.warn(`[CI/CD Interceptor Warning] Pipeline stderr:\n${stderr}`);
              }
              console.log(`[CI/CD Interceptor Success] Pipeline completed successfully. Output:\n${stdout}`);
            });
          }
        });
      },
    },
  });
});
