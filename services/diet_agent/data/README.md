# External Recipe Data

To use a Kaggle recipe CSV instead of the built-in local recipe catalog, either:

- place the downloaded CSV here as `recipe_final.csv`, or
- place the Epicurious Kaggle CSV here as `epi_r.csv`, or
- set `KAGGLE_RECIPE_CSV` to the absolute CSV path.

Supported columns include common Kaggle names such as `recipe_name`, `calories`,
`fat`, `carbohydrates`, `protein`, `ingredients_list`, and `description`.

The Epicurious `epi_r.csv` format is also supported. It uses `title`, `rating`,
`calories`, `protein`, `fat`, `sodium`, and one-hot recipe tag columns. That file
does not include ingredient grams or full recipe steps, so the app uses its tags
as ingredient/category hints and keeps the nutrition values from the CSV.
