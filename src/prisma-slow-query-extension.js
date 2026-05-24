const { Prisma } = require('@prisma/client');
const { exec } = require('child_process');
const { performance } = require('perf_hooks');

/**
 * JavaScript version of the slow query interceptor for local testing.
 */
const slowQueryInterceptor = Prisma.defineExtension((client) => {
  return client.$extends({
    query: {
      $allOperations({ model, operation, args, query }) {
        const start = performance.now();

        return query(args).finally(() => {
          const duration = performance.now() - start;

          // Threshold: 500ms
          if (duration > 500) {
            console.warn(
              `⚠️ [SLOW QUERY DETECTED] Model: ${model || 'RawQuery'}, Operation: ${operation} took ${duration.toFixed(2)}ms`
            );

            // Execute the pipeline scripts from the correct optimization_artifacts path
            const cmd = 'python optimization_artifacts/run_phase_2.py && python optimization_artifacts/run_phase_3.py';

            console.log(`[CI/CD Interceptor] Spawning optimizer: "${cmd}"...`);

            exec(cmd, { env: { ...process.env, PYTHONIOENCODING: 'utf-8' } }, (error, stdout, stderr) => {
              if (error) {
                console.error(`[CI/CD Interceptor Error] Run failed: ${error.message}`);
                return;
              }
              if (stderr) {
                console.warn(`[CI/CD Interceptor Warning] Stderr:\n${stderr}`);
              }
              console.log(`[CI/CD Interceptor Success] Pipeline completed successfully. Output:\n${stdout}`);
            });
          }
        });
      },
    },
  });
});

module.exports = { slowQueryInterceptor };
