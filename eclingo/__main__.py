import argparse
from time import perf_counter as timer
import eclingo.main as eclingo


def main():
    print(f'eclingo version {eclingo.__version__}')

    argparser = argparse.ArgumentParser(prog='eclingo')
    argparser.add_argument('-n', '--world-views', type=int,
                           help='maximum number of world views to compute '
                           '(0 computes all world views)', default=1)
    argparser.add_argument('-a', '--answer-sets', type=int,
                           help='maximum number of answer sets to compute for each world view ' +
                           '(0 computes all answer sets)')
    argparser.add_argument('-k', '--k15', action='store_true',
                           help='computes world views under K15 semantics')
    argparser.add_argument('-op', '--optimization', type=int,
                           help='number of optimization to use (0 for no optimizations)',
                           default=eclingo.__optimization__)
    argparser.add_argument('-c', '--const', action='append',
                           help='adds a constant to the program (using \'<name>=<term>\' format)')
    argparser.add_argument('input_files', nargs='+', type=str, help='path to input files')
    args = argparser.parse_args()

    start = timer()

    eclingo_control = eclingo.Control(max_world_views=args.world_views,
                                      semantics=args.k15,
                                      optimization=args.optimization)

    for file_path in args.input_files:
        eclingo_control.load(file_path)
    if args.const:
        for constant in args.const:
            name, term = constant.split('=')
            eclingo_control.add_const(name, term)

    eclingo_control.parse()
    print('Solving...')
    for world_view in eclingo_control.solve():
        print(f'World view: {eclingo_control.world_views}\n{world_view}')
        if isinstance(args.answer_sets, int):
            print('==> Begin World view <==')
            for answer_set_index, answer_set in \
                    enumerate(world_view.get_answer_sets(args.answer_sets)):
                print(f'Answer: {answer_set_index+1}\n{answer_set}')
            print('========================')

    end = timer()

    print('SATISFIABLE\n') if eclingo_control.world_views else print('UNSATISFIABLE\n')

    exhausted = '+' if not eclingo_control.exhausted else ''
    print(f'World views\t: {eclingo_control.world_views}{exhausted}\n' +
          f'Elapsed time\t: {(end-start):.6f} s')


if __name__ == "__main__":
    main()
