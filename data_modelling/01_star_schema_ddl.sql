-- Date Dimension Generator
-- 1. Create dim_date
CREATE TABLE dim_date (
    date_key INT PRIMARY KEY,
    full_date DATE NOT NULL,
    day_of_week VARCHAR(10),
    day_name VARCHAR(10),
    day_of_month INT,
    month_number INT,
    month_name VARCHAR(10),
    quarter_number INT,
    year_number INT,
    is_weekend BOOLEAN
);

-- Customer Dimension
CREATE TABLE dim_customer (
    customer_key SERIAL PRIMARY KEY,
    customer_id INT UNIQUE,
    city VARCHAR(50),
    signup_date DATE
);

-- Product Dimension (Conformed with Categories & Suppliers)
CREATE TABLE dim_product (
    product_key SERIAL PRIMARY KEY,
    product_id INT UNIQUE,
    category_name VARCHAR(100),
    supplier_country VARCHAR(100),
    retail_list_price NUMERIC(10, 2),
    wholesale_cost NUMERIC(10, 2)
);


-- Store Dimension
CREATE TABLE dim_store (
    store_key SERIAL PRIMARY KEY,
    store_id INT UNIQUE,
    city VARCHAR(50)
);


-- Promoton Dimension
CREATE TABLE dim_promotion (
    promotion_key SERIAL PRIMARY KEY,
    promotion_id INT UNIQUE,
    discount NUMERIC(10, 2)
);


-- Fact_Sales
CREATE TABLE fact_sales (
    sales_key SERIAL PRIMARY KEY,
    order_item_id INT,
    order_id INT,
    customer_key INT REFERENCES dim_customer(customer_key),
    product_key INT REFERENCES dim_product(product_key),
    store_key INT REFERENCES dim_store(store_key),
    promotion_key INT REFERENCES dim_promotion(promotion_key),
    order_date_key INT REFERENCES dim_date(date_key),
    shipment_status VARCHAR(50),
    qty INT,
    unit_price NUMERIC(10, 2),
    gross_revenue NUMERIC(10, 2),
    discount_amount NUMERIC(10, 2),
    net_revenue NUMERIC(10, 2),
    refund_amount NUMERIC(10, 2),
    final_revenue NUMERIC(10, 2),
    cost_amount NUMERIC(10, 2),
    net_profit NUMERIC(10, 2)
);


-- DDL for fact_order_payments
CREATE TABLE fact_order_payments (
    payment_fact_key SERIAL PRIMARY KEY,
    payment_id INT,
    order_id INT,
    customer_key INT REFERENCES dim_customer(customer_key),
    store_key INT REFERENCES dim_store(store_key),
    order_date_key INT REFERENCES dim_date(date_key),
    payment_amount NUMERIC(10, 2)
);


-- DDL for fact_store_payroll
CREATE TABLE fact_store_payroll (
    payroll_key SERIAL PRIMARY KEY,
    employee_id INT,
    store_key INT REFERENCES dim_store(store_key),
    salary NUMERIC(10, 2)
);
