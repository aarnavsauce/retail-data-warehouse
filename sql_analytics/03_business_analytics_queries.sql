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

-- Query 2 -  Customer Recency, Frequency, Monetary (RFM) Segmentation

WITH customer_aggregates AS (
    SELECT 
        c.customer_key,
        c.customer_id,
        c.city,
        c.signup_date,
        MAX(d.full_date) AS last_order_date,
        -- Calculate Recency: days between last purchase date and reference snapshot date (2026-12-31)
        ('2026-12-31'::DATE - MAX(d.full_date)) AS recency_days,
        COUNT(DISTINCT f.order_id) AS order_frequency,
        SUM(f.final_revenue) AS total_monetary_spend
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY c.customer_key, c.customer_id, c.city, c.signup_date
),
rfm_scores AS (
    SELECT 
        customer_id,
        city,
        signup_date,
        last_order_date,
        recency_days,
        order_frequency,
        total_monetary_spend,
        -- Score 5 is best for Recency (lowest recency_days = highest score)
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        -- Score 5 is best for Frequency (highest order count = highest score)
        NTILE(5) OVER (ORDER BY order_frequency ASC) AS f_score,
        -- Score 5 is best for Monetary (highest total spend = highest score)
        NTILE(5) OVER (ORDER BY total_monetary_spend ASC) AS m_score
    FROM customer_aggregates
)
SELECT 
    customer_id,
    city,
    signup_date,
    last_order_date,
    recency_days,
    order_frequency,
    total_monetary_spend,
    r_score,
    f_score,
    m_score,
    (r_score + f_score + m_score) AS composite_rfm_score,
    CASE 
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions / VIP'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score <= 2 AND f_score >= 4 THEN 'At Risk (High-Value Churning)'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Hibernating / Lost'
        ELSE 'Standard Customer'
    END AS customer_segment
FROM rfm_scores
ORDER BY total_monetary_spend DESC;

-- Query 3 - Fulfillment Status and Category Return Rate Analysis
WITH fulfillment_summary AS (
    SELECT 
        COALESCE(shipment_status, 'Unshipped / Pending') AS shipment_status,
        COUNT(DISTINCT order_id) AS order_count,
        SUM(gross_revenue) AS gross_revenue_impact,
        SUM(final_revenue) AS net_revenue_impact
    FROM fact_sales
    GROUP BY COALESCE(shipment_status, 'Unshipped / Pending')
),
category_returns AS (
    SELECT 
        p.category_name,
        COUNT(f.sales_key) AS total_items_sold,
        COUNT(CASE WHEN f.refund_amount > 0 THEN 1 END) AS returned_items_count,
        SUM(f.gross_revenue) AS gross_category_revenue,
        SUM(f.discount_amount) AS total_discounts_given,
        SUM(f.refund_amount) AS total_refunded_amount,
        SUM(f.final_revenue) AS net_category_revenue
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key
    GROUP BY p.category_name
)
SELECT 
    cr.category_name,
    cr.total_items_sold,
    cr.returned_items_count,
    -- Return Rate Percentage: (Returned Items / Total Items Sold) * 100
    ROUND((cr.returned_items_count::NUMERIC / NULLIF(cr.total_items_sold, 0)) * 100, 2) AS return_rate_pct,
    cr.gross_category_revenue,
    cr.total_refunded_amount,
    -- Refund Erosion Rate Percentage: (Refunded Amount / Gross Category Revenue) * 100
    ROUND((cr.total_refunded_amount / NULLIF(cr.gross_category_revenue, 0)) * 100, 2) AS refund_revenue_loss_pct,
    cr.net_category_revenue
FROM category_returns cr
ORDER BY return_rate_pct DESC;