require("dotenv").config();

const express = require("express");
const cors = require("cors");
const { GoogleGenerativeAI } = require("@google/generative-ai");

const app = express();

app.use(cors());
app.use(express.json());

const PORT = 3000;

// ---------------- GEMINI SETUP ----------------

const genAI = new GoogleGenerativeAI(
  process.env.GEMINI_API_KEY
);

// ---------------- SAMPLE QUERIES ----------------

const queries = [
  {
    sql: `
      SELECT * FROM users
      WHERE email LIKE '%gmail.com%'
    `,
    issue: "Missing Index",
  },

  {
    sql: `
      SELECT * FROM orders
      ORDER BY createdAt DESC
    `,
    issue: "Full Table Scan",
  },

  {
    sql: `
      SELECT * FROM posts
      WHERE title LIKE '%AI%'
    `,
    issue: "Inefficient LIKE Query",
  },

  {
    sql: `
      SELECT * FROM products
      WHERE price > 1000
    `,
    issue: "No Filtering Index",
  }
];

// ---------------- HOME ROUTE ----------------

app.get("/", (req, res) => {

  res.json({
    message: "AI Database Optimizer Running 🚀",
    status: "ACTIVE"
  });

});

// ---------------- AI ANALYZER ROUTE ----------------

app.get("/analyze", async (req, res) => {

  try {

    const start = Date.now();

    // random query simulation
    const randomQuery =
      queries[Math.floor(Math.random() * queries.length)];

    const sqlQuery = randomQuery.sql;

    // simulate slow database
    await new Promise(resolve =>
      setTimeout(resolve, 2000)
    );

    const end = Date.now();

    const queryTime = end - start;

    let aiAnalysis = {};

    // ---------------- DETECT SLOW QUERY ----------------

    if (queryTime > 1000) {

      console.log("⚠️ SLOW QUERY DETECTED");

      try {

        // ---------------- GEMINI MODEL ----------------

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

        console.log("Gemini API Failed");

        // ---------------- FALLBACK RESPONSE ----------------

        aiAnalysis = {
          source: "Fallback AI Engine",
          issue: randomQuery.issue,
          severity: "High",
          recommendation:
            "Add indexing, pagination, and caching",
          optimizationSQL:
            "CREATE INDEX idx_email ON users(email);",
          estimatedImprovement: "70%",
        };

      }

    }

    // ---------------- FINAL RESPONSE ----------------

    res.json({

      success: true,

      project: "AI-Powered Database Optimizer",

      slowQueryDetected: true,

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

// ---------------- SERVER START ----------------

app.listen(PORT, () => {

  console.log(`
==========================================
🚀 AI Database Optimizer Running
🌐 Server: http://localhost:${PORT}
📊 Analyze: http://localhost:${PORT}/analyze
==========================================
`);

});