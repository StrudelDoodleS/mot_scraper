# Data

In this csv you will find what is essentially a lookup table for MOT codes and there severity. The key for joins should be full_reference_code.

The easiest way to download the data without clicking the download button is this:

```python
import pandas as pd

url = "https://raw.githubusercontent.com/StrudelDoodleS/mot_scraper/data/mot_table.csv"
df = pd.read_csv(url, index_col=0)

# df.to_pickle('your/path/here')

```
