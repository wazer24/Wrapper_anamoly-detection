-- =============================================================================
-- PostgreSQL Index Migration
-- Winner: H1 (Composite B-Tree on orders)
-- =============================================================================
--
-- Performance Gains:
--   - Local Seeded DB Cost Reduction: 12.37% (Total Plan), 62.32% (Orders Scan)
--   - Projected Production Cost Reduction: 66.50% (Saves ~9,500ms execution time)
--   - Eliminates: Sequential Scan on orders table by converting it to a Bitmap Index Scan
--
-- Rationale:
--   Allows PostgreSQL to quickly filter orders by status ('completed', 'shipped')
--   and range scan by created_at in descending order.
-- =============================================================================

CREATE INDEX CONCURRENTLY idx_orders_status_created_at 
ON orders (status, created_at DESC);
