import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function seed() {
  console.log('Seeding...');
  for (let i = 1; i <= 10; i++) {
    await prisma.customer.create({
      data: {
        email: `user${i}@test.com`,
        full_name: `Test User ${i}`,
      }
    });
  }

  for (let i = 1; i <= 50; i++) {
    await prisma.order.create({
      data: {
        customerId: (i % 10) + 1,
        status: i % 3 === 0 ? 'pending' : 'shipped',
      }
    });
  }
  console.log('Done!');
}

seed().catch(console.error).finally(() => prisma.$disconnect());
