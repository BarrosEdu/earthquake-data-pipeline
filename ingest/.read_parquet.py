import pyarrow.dataset as ds
import pandas as pd

def read_silver_all(base_dir: str = "./data/silver/earthquakes"):
    dataset = ds.dataset(base_dir, format="parquet", partitioning="hive")  # entende date=YYYY-MM-DD
    table = dataset.to_table()  # lê tudo
    df = table.to_pandas()
    # se a coluna 'date' vier como string, converta:
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    return df

df = read_silver_all()

print(df)