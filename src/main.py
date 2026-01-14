import sys
from pathlib import Path
from etl.pipelines import pipeline_db_raw
from etl.pipelines import pipeline_db_cleaned

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


if __name__ == "__main__":

    #pipeline_db_raw()
    pipeline_db_cleaned()