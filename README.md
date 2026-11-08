# Enterprise Retail Data Warehouse & BI Architecture

## Overview
This project models an enterprise retail data warehouse in PostgreSQL using Kimball Star Schema architecture. It transforms raw transactional data into conformed dimensions and multi-grain fact tables for executive analytics.

## Data Warehouse Architecture
* **Conformed Dimensions:** `dim_customer`, `dim_store`, `dim_product`, `dim_promotion`, `dim_date`
* **Fact Tables:** 
  * `fact_sales` (Item-level sales transactions, pricing, discounts, refunds)
  * `fact_order_payments` (Header-level payment reconciliation)
  * `fact_store_payroll` (Periodic store operational overhead)

## Project Structure
* `data_modeling/`: DDL scripts for Star Schema tables
* `etl_pipeline/`: Data cleaning and transformation queries
* `sql_analytics/`: Advanced analytical queries (RFM segmentation, rolling growth metrics)