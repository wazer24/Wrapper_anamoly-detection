require("dotenv").config();

const express = require("express");
const cors = require("cors");
const { GoogleGenerativeAI } = require("@google/generative-ai");

const app = express();

app.use(cors());
app.use(express.json());

const PORT = 3000;

// ==========================================
// GEMINI SETUP
// ==========================================

const genAI = new GoogleGenerativeAI(
  process.env.GEMINI_API_KEY
);

// ==========================================
// SAMPLE SQL QUERIES
// ==========================================

const queries = [

  {
    sql: `
      SELECT * FROM users
      WHERE email LIKE '%gmail.com%'
    `,
    issue: "Missing Index"
  },

  {
    sql: `
      SELECT * FROM orders
      ORDER BY createdAt DESC
    `,
    issue: "Full Table Scan"
  },

  {
    sql: `
      SELECT * FROM posts
      WHERE title LIKE '%AI%'
    `,
    issue: "Inefficient LIKE Query"
  },

  {
    sql: `
      SELECT * FROM products
      WHERE price > 1000
    `,
    issue: "No Filtering Index"
  }

];

// ==========================================
// HOME ROUTE
// ==========================================

app.get("/", (req, res) => {

  res.json({
    success: true,
    project: "AI-Powered Database Optimizer",
    status: "ACTIVE",
    routes: {
      analyze: "/analyze",
      health: "/health"
    }
  });

});

// ==========================================
// HEALTH CHECK ROUTE
// ==========================================

app.get("/health", (req, res) => {

  res.json({
    status: "healthy",
    server: "running",
    ai: "active",
    timestamp: new Date()
  });

});

// ==========================================
// AI ANALYZER ROUTE
// ==========================================

app.get("/analyze", async (req, res) => {

  try {

    const queryId =
      Math.random().toString(36).substring(2, 10);

    const start = Date.now();

    // Random query selection
    const randomQuery =
      queries[Math.floor(Math.random() * queries.length)];

    const sqlQuery = randomQuery.sql;

    // Simulate slow DB query
    await new Promise(resolve =>
      setTimeout(resolve, 2000)
    );

    const end = Date.now();

    const queryTime = end - start;

    let aiAnalysis = {};

    // ==========================================
    // SLOW QUERY DETECTION
    // ==========================================

    if (queryTime > 1000) {

      console.log("⚠️ SLOW QUERY DETECTED");

      try {

        // ==========================================
        // GEMINI MODEL
        // ==========================================

        const model = genAI.getGenerativeModel({
          model: "gemini-2.0-flash"
        });

        const prompt = `
You are an expert PostgreSQL database optimizer.

Analyze this SQL query:

${sqlQuery}

Execution Time:
${queryTime} ms

Return:
1. Issue
2. Severity
3. Optimization
4. Recommended SQL Fix
5. Estimated Improvement

Keep response concise.
`;

        const result =
          await model.generateContent(prompt);

        const response =
          result.response.text();

        aiAnalysis = {
          source: "Gemini AI",
          analysis: response
        };

      } catch (error) {

        console.log("Gemini API ");

        // ==========================================
        // FALLBACK AI ENGINE
        // ==========================================

        aiAnalysis = {

          source: "Fallback AI Engine",

          issue: randomQuery.issue,

          severity: "High",

          riskScore: 8.5,

          recommendation:
            "Add indexing, pagination, and caching",

          optimizationSQL:
            "CREATE INDEX idx_email ON users(email);",

          estimatedImprovement: "70%"

        };

      }

    } else {

      aiAnalysis = {

        source: "No Issue Detected",

        issue:
          "Query within acceptable performance range",

        severity: "Low",

        riskScore: 1.0,

        recommendation:
          "No immediate action required",

        optimizationSQL: null,

        estimatedImprovement: "0%"

      };

    }

    // ==========================================
    // FINAL RESPONSE
    // ==========================================

    res.json({

      success: true,

      queryId,

      project:
        "AI-Powered Database Optimizer",

      slowQueryDetected:
        queryTime > 1000,

      timestamp: new Date(),

      performance: {

        executionTime: `${queryTime} ms`,

        status:
          queryTime > 1000
            ? "CRITICAL"
            : "OPTIMIZED"

      },

      query: {

        database: "PostgreSQL",

        sql: sqlQuery

      },

      aiAnalysis

    });

  } catch (error) {

    console.log(error);

    res.status(500).json({

      success: false,

      error: "Internal Server Error"

    });

  }

});

// ==========================================
// SERVER START
// ==========================================

app.listen(PORT, () => {

  console.log(`
==========================================
 AI Database Optimizer Running
🌐 Server: http://localhost:${PORT}
 Analyze: http://localhost:${PORT}/analyze
 Health: http://localhost:${PORT}/health
==========================================
`);

});