import sys

import biomass.raw_generator

helptext = """\
Usage:
    raw_generator <path> <start_time> <end_time>
"""


def main(args):
    biomass.raw_generator.main()


if __name__ == "__main__":
    main(sys.argv[1:])
