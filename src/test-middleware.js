const { PrismaClient } = require('@prisma/client');
const { slowQueryInterceptor } = require('./src/prisma-slow-query-extension');

const basePrisma = new PrismaClient({
  log: ['query']
});

const prisma = basePrisma.$extends(slowQueryInterceptor);

async function test() {
  console.log("=" * 60);
  console.log("🚀 Testing Prisma Slow Query Interceptor");
  console.log("=" * 60);
  
  try {
    console.log("\nExecuting standard query (should be fast)...");
    await prisma.customer.findMany({ take: 1 });
    console.log("✅ Standard query finished.");
    
    console.log("\nExecuting simulated slow query (SELECT pg_sleep(0.6)::text)...");
    await prisma.$queryRawUnsafe('SELECT pg_sleep(0.6)::text;');
    console.log("✅ Simulated slow query finished. Waiting for optimizer background run...");
    
    // Allow 5 seconds for the background optimizer to execute and report
    setTimeout(() => {
      console.log("\nTest run completed.");
      process.exit(0);
    }, 5000);
    
  } catch (err) {
    console.error("❌ Test failed with error:", err);
    process.exit(1);
  }
}

test();
