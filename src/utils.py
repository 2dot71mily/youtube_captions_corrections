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


def split_files_by_lines(reading_path, writing_path, writing_filename, n_lines):
    path = Path(reading_path)
    print(f"reading from {reading_path}")

    all_names = [
        f.name for f in path.iterdir() if f.is_file() and f.suffix.lower() == ".json"
    ]
    all_dfs = [pd.read_json(str(PurePath(path, f_name))) for f_name in all_names]

    df = pd.concat(all_dfs, ignore_index=True)

    dups = df[df.index.duplicated()].index
    df.drop(dups, inplace=True)

    len_df = len(df)
    chunks = list(range(0, len_df + 1, n_lines))
    if chunks[-1] != len_df:
        chunks.append(len_df)

    Path(writing_path).mkdir(parents=True, exist_ok=True)
    for i in range(len(chunks) - 1):
        df.iloc[chunks[i] : chunks[i + 1]].to_json(
            str(PurePath(writing_path, f"{writing_filename}_{i}.json"))
        )
    print(f"saved files to {writing_path}")


if __name__ == "__main__":

    read_path = config.POSTPROC_TRANSCRIPT_PATH
    write_path = config.SPLIT_LABELED_PATH
    input(
        f"""
        Running this file directly will concat all dfs together in: 
        {read_path} 
        and write to:
        {write_path}. 
        [Ctrl+c] to quit or [Enter] to continue.
        """
    )

    split_files_by_lines(
        read_path, write_path, config.SPLIT_LABELED_FILENAME, config.SPLIT_FILE_N_LINES
    )
