-- following query queried after the creation of fact and dimension tables. 

SELECT 
    SUM(gross_revenue) AS total_gross,
    SUM(discount_amount) AS total_discounts,
    SUM(refund_amount) AS total_refunds,
    SUM(final_revenue) AS total_final_revenue,
    SUM(p.wholesale_price * f.qty) AS calculated_cost
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key;
