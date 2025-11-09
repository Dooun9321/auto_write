-- Sample BigQuery queries for reference
-- These will be analyzed by the agent to learn query patterns

-- Example 1: Top customers by revenue
SELECT
    customer_id,
    customer_name,
    SUM(order_amount) as total_revenue,
    COUNT(DISTINCT order_id) as total_orders,
    AVG(order_amount) as avg_order_value
FROM
    `project.dataset.orders`
WHERE
    order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    AND order_status = 'completed'
GROUP BY
    customer_id,
    customer_name
ORDER BY
    total_revenue DESC
LIMIT 10;

-- Example 2: Monthly trend analysis
WITH monthly_stats AS (
    SELECT
        FORMAT_DATE('%Y-%m', order_date) as month,
        COUNT(DISTINCT customer_id) as unique_customers,
        COUNT(order_id) as total_orders,
        SUM(order_amount) as total_revenue
    FROM
        `project.dataset.orders`
    WHERE
        order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    GROUP BY
        month
)
SELECT
    month,
    unique_customers,
    total_orders,
    total_revenue,
    LAG(total_revenue) OVER (ORDER BY month) as prev_month_revenue,
    ROUND((total_revenue - LAG(total_revenue) OVER (ORDER BY month)) / LAG(total_revenue) OVER (ORDER BY month) * 100, 2) as revenue_growth_pct
FROM
    monthly_stats
ORDER BY
    month DESC;

-- Example 3: Product performance analysis
SELECT
    p.product_id,
    p.product_name,
    p.category,
    COUNT(DISTINCT o.order_id) as times_ordered,
    SUM(o.quantity) as total_quantity_sold,
    SUM(o.revenue) as total_revenue,
    AVG(o.unit_price) as avg_unit_price,
    COUNT(DISTINCT o.customer_id) as unique_buyers
FROM
    `project.dataset.products` p
INNER JOIN
    `project.dataset.order_items` o ON p.product_id = o.product_id
WHERE
    o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
GROUP BY
    p.product_id,
    p.product_name,
    p.category
HAVING
    times_ordered >= 10
ORDER BY
    total_revenue DESC;

-- Example 4: Cohort analysis
WITH user_cohorts AS (
    SELECT
        user_id,
        DATE_TRUNC(MIN(signup_date), MONTH) as cohort_month
    FROM
        `project.dataset.users`
    GROUP BY
        user_id
),
user_activity AS (
    SELECT
        uc.user_id,
        uc.cohort_month,
        DATE_TRUNC(a.activity_date, MONTH) as activity_month,
        DATE_DIFF(DATE_TRUNC(a.activity_date, MONTH), uc.cohort_month, MONTH) as months_since_signup
    FROM
        user_cohorts uc
    JOIN
        `project.dataset.user_activity` a ON uc.user_id = a.user_id
)
SELECT
    cohort_month,
    months_since_signup,
    COUNT(DISTINCT user_id) as active_users
FROM
    user_activity
WHERE
    cohort_month >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
GROUP BY
    cohort_month,
    months_since_signup
ORDER BY
    cohort_month,
    months_since_signup;

-- Example 5: Window function for ranking
SELECT
    order_date,
    customer_id,
    order_amount,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) as order_recency_rank,
    RANK() OVER (PARTITION BY DATE_TRUNC(order_date, MONTH) ORDER BY order_amount DESC) as monthly_amount_rank,
    SUM(order_amount) OVER (PARTITION BY customer_id ORDER BY order_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as cumulative_customer_spending
FROM
    `project.dataset.orders`
WHERE
    order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)
ORDER BY
    customer_id,
    order_date DESC;
