import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import argparse

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("target", type=str)
    args = argparser.parse_args()
    match args.target:
        case 'yolo':
            import ultralytics
            ultralytics.YOLO(verbose=True)
            exit()
        case 'ocr':
            import easyocr
            easyocr.Reader(["en"], model_storage_directory=".", verbose=True)
            exit()
        case _:
            raise ValueError("No matching setup target")