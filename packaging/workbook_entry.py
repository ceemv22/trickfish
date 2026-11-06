import sys


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        from trickfish.workbook_smoke import run

        run(sys.argv[2])
    else:
        from trickfish.workbook_gui import main

        main()
