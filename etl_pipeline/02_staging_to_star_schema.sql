-- Populate dim_date with calendar logic
INSERT INTO dim_date
SELECT 
    TO_CHAR(d, 'YYYYMMDD')::INT AS date_key,
    d::DATE AS full_date,
    TO_CHAR(d, 'ID') AS day_of_week,
    TO_CHAR(d, 'Day') AS day_name,
    EXTRACT(DAY FROM d) AS day_of_month,
    EXTRACT(MONTH FROM d) AS month_number,
    TO_CHAR(d, 'Month') AS month_name,
    EXTRACT(QUARTER FROM d) AS quarter_number,
    EXTRACT(YEAR FROM d) AS year_number,
    CASE WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend
FROM GENERATE_SERIES('2020-01-01'::DATE, '2026-12-31'::DATE, '1 day'::INTERVAL) d;

-- Populate dim_customer
INSERT INTO dim_customer (customer_id, city, signup_date)
SELECT DISTINCT customer_id, city, signup_date::DATE
FROM staging_customers;

-- Populate dim_product 
-- BUSINESS RULE ASSUMPTION: 
-- Raw dataset lacks explicit wholesale cost column.
-- Applying standard retail COGS model (60% of retail list price) to estimate wholesale cost.
INSERT INTO dim_product (product_id, category_name, supplier_country, wholesale_price)
SELECT 
    p.product_id,
    c.category_name,
    s.country AS supplier_country,
    ROUND((p.price * 0.60), 2) AS wholesale_price -- what is wholesale_price?
FROM staging_products p
LEFT JOIN staging_categories c ON p.category_id = c.category_id
LEFT JOIN staging_suppliers s ON p.supplier_id = s.supplier_id;

-- Populate dim_store
INSERT INTO dim_store (store_id, city)
SELECT DISTINCT store_id, city
FROM staging_stores;

-- Populate dim_promotions
INSERT INTO dim_promotion (promotion_id, discount)
SELECT DISTINCT promotion_id, discount
FROM staging_promotions;

-- Populate fact_sales
INSERT INTO fact_sales (
    order_item_id,
    order_id,
    customer_key,
    product_key,
    store_key,
    promotion_key,
    order_date_key,
    shipment_status,
    qty,
    unit_price,
    gross_revenue,
    discount_amount,
    net_revenue,
    refund_amount,
    final_revenue
)
SELECT 
    oi.order_item_id,
    o.order_id,
    c.customer_key,
    p.product_key,
    s.store_key,
    pr.promotion_key,
    TO_CHAR(o.order_date, 'YYYYMMDD')::INT AS order_date_key,
    shp.status AS shipment_status,
    oi.qty,
    oi.price AS unit_price,
    (oi.qty * oi.price) AS gross_revenue,
    
    -- Divide discount by 100.0 to convert whole numbers (e.g., 15) to decimals (0.15)
    ROUND((oi.qty * oi.price * (COALESCE(pr.discount, 0) / 100.0)), 2) AS discount_amount,
    
    (oi.qty * oi.price) - ROUND((oi.qty * oi.price * (COALESCE(pr.discount, 0) / 100.0)), 2) AS net_revenue,
    COALESCE(ret.refund, 0) AS refund_amount,
    ((oi.qty * oi.price) - ROUND((oi.qty * oi.price * (COALESCE(pr.discount, 0) / 100.0)), 2)) - COALESCE(ret.refund, 0) AS final_revenue

FROM staging_order_items oi
JOIN staging_orders o ON oi.order_id = o.order_id
LEFT JOIN dim_customer c ON o.customer_id = c.customer_id
LEFT JOIN dim_product p ON oi.product_id = p.product_id
LEFT JOIN dim_store s ON o.store_id = s.store_id
LEFT JOIN dim_promotion pr ON o.promotion_id = pr.promotion_id
LEFT JOIN staging_returns ret ON oi.order_item_id = ret.order_item_id
LEFT JOIN staging_shipments shp ON o.order_id = shp.order_id;

-- Populate fact_order_payments
INSERT INTO fact_order_payments (payment_id, order_id, customer_key, store_key, order_date_key, payment_amount)
SELECT 
    pay.payment_id,
    o.order_id,
    c.customer_key,
    s.store_key,
    TO_CHAR(o.order_date, 'YYYYMMDD')::INT AS order_date_key,
    pay.amount
FROM staging_payments pay
JOIN staging_orders o ON pay.order_id = o.order_id
LEFT JOIN dim_customer c ON o.customer_id = c.customer_id
LEFT JOIN dim_store s ON o.store_id = s.store_id;

-- Populate fact_store_payroll
INSERT INTO fact_store_payroll (employee_id, store_key, salary)
SELECT 
    e.employee_id,
    s.store_key,
    e.salary
FROM staging_employees e
LEFT JOIN dim_store s ON e.store_id = s.store_id;