from src.utils.start_server import start_server


def run(args):
    return start_server(verbose=args.verbose)
