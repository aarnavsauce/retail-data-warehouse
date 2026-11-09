-- Query 1 - Analytics query to calculate Monthly Revenue, Wholesale Cost Margin & 3-Month Average

WITH monthly_financials AS (
    SELECT 
        d.year_number,
        d.month_number,
        d.month_name,
        COUNT(DISTINCT f.order_id) AS total_orders,
        SUM(f.gross_revenue) AS gross_revenue,
        SUM(f.discount_amount) AS total_discounts,
        SUM(f.refund_amount) AS total_refunds,
        SUM(f.final_revenue) AS final_revenue,
        SUM(f.cost_amount) AS total_cost,
        SUM(f.net_profit) AS total_net_profit
    FROM fact_sales f
    JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY d.year_number, d.month_number, d.month_name
)
SELECT 
    year_number,
    month_name,
    total_orders,
    gross_revenue,
    total_discounts,
    total_refunds,
    final_revenue,
    total_cost,
    total_net_profit,
    ROUND((total_net_profit / NULLIF(final_revenue, 0)) * 100, 2) AS net_profit_margin_pct,
    ROUND(
        AVG(final_revenue) OVER (
            ORDER BY year_number, month_number 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_3m_avg_revenue
FROM monthly_financials
ORDER BY year_number, month_number;