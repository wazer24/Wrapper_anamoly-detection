import express from "express";

const app = express();

app.get("/", async (req, res) => {

  const start = Date.now();

  // fake slow database query
  await new Promise(resolve => setTimeout(resolve, 2000));

  const end = Date.now();

  const queryTime = end - start;

  let aiSuggestion = "";

  if (queryTime > 1000) {
    console.log("SLOW QUERY DETECTED");

    aiSuggestion = "Use indexing, pagination, or caching";
  }

  res.json({
    message: "AI DB Optimizer Working",
    queryTime: `${queryTime} ms`,
    aiSuggestion
  });

});

app.listen(3000, () => {
  console.log("Server running on port 3000");
});