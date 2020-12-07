import pandas as pd
from pathlib import PurePath, Path

import config


def open_file_or_create(gen_data_func, root_resource, file_path, file_name, **kwargs):

    try:  # to get already requested and saved data
        full_path = str(PurePath(file_path, f"{file_name}.json"))
        data_df = pd.read_json(full_path)
        print(f"reading {full_path}")

    except ValueError:
        Path(file_path).mkdir(parents=True, exist_ok=True)
        print(f"requesting data for {full_path}")
        data_df = gen_data_func(root_resource, file_path, file_name, **kwargs)

    return data_df


def save_and_rem_files(df, file_path, file_name, i=0, save_interval=100, end=False):
    if end:
        full_path = str(PurePath(file_path, f"{file_name}.json"))

        df.to_json(full_path)

        if i > save_interval:
            file_to_rem = Path(
                file_path, f"i{i - (i % save_interval)}_{file_name}.json"
            )
            file_to_rem.unlink()
    else:
        df.to_json(str(PurePath(file_path, f"i{i}_{file_name}.json")))
        if i > save_interval:
            file_to_rem = Path(file_path, f"i{i - save_interval}_{file_name}.json")
            file_to_rem.unlink()


def concat_all_dataframes_in_dir(reading_path, writing_path, writing_filename):
    path = Path(reading_path)
    print(f"reading from {reading_path}")

    all_dfs = [pd.read_json(f) for f in path.iterdir() if f.is_file() and f.suffix.lower() =='.json']
    df = pd.concat(all_dfs)

    dups = df[df.index.duplicated()].index
    df.drop(dups, inplace=True)

    Path(writing_path).mkdir(parents=True, exist_ok=True)
    full_filename = str(PurePath(writing_path, f"{writing_filename}.json"))
    df.to_json(full_filename)
    print(f"saved {full_filename}")


if __name__ == "__main__":
    
    read_path = config.LABELED_TRANSCRIPT_PATH
    write_path = config.COMBINED_LABELED_PATH
    input(
        f"""
        Running this file directly will concat all dfs together in: 
        {read_path} 
        and write to:
        {write_path}. 
        [Ctrl+c] to quit or [Enter] to continue.
        """
    )
    
    concat_all_dataframes_in_dir(
        read_path, config.COMBINED_LABELED_PATH, config.COMBINED_LABELED_FILENAME
    )
