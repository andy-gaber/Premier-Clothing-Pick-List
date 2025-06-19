This application was developed for an eCommerce business that receives approximately 200 daily online orders. The items from every order must be physically picked from the company’s sizable inventory warehouse before being packed and shipped. Order-picking is a time-consuming effort, yet the company strives to provide exceptional customer service by shipping orders within 24 hours of purchase.

The application parses a large volume of customers' orders JSON data to generate a sorted list (i.e. pick list) of all items and their quantities ordered alphanumerically by Stock Keeping Unit (SKU). This allows items to be picked in order by warehouse location. Before this application was developed the company used a web-based order management platform to generate a generic pick list that was arbitrary and unordered (example below) which resulted in inefficient order-picking and a significant waste of time and resources.

<img width="432" alt="before" src="https://github.com/user-attachments/assets/f9ad2920-5b21-4c97-a6bc-e3d3c3b96299" />

The business sells apparel through five separete online stores, and each store’s customers' order JSON data is requested from a web-based order management platform. The data from each store is parsed, cleaned, and normalized before collectively being sorted. Items are first grouped by SKU. Then, since every item is available in multiple sizes each SKU's sizes are sorted logically (e.g. "SML" < "MED" < "LRG"). Finally the complete pick list is sorted alphanumerically as seen in the example below.

<img width="748" alt="after" src="https://github.com/user-attachments/assets/fc51691b-1cfc-4045-87ff-ccc689f6cb14" />

This application is used daily and updated when necessary (originally when bugs were discovered, but now only when SKUs are changed or new inventory is added... no bugs in a long time!). It resulted in an optimization of order-processing and a reduction in the time to pick inventory items by approximately 50 percent.
