import clingo


def _generate_projection_directives(k_signatures):
    string = ''
    for (name, arity, _) in k_signatures:
        string = string + ('#project %s/%d.\n' % (name, arity))
        string = string + ('#show %s/%d.\n' % (name, arity))

    return string


def _add_const(constants, control_objects):
    constants_string = ''
    for const in constants:
        constants_string += ('#const %s.' % const)
    for control_object in control_objects:
        control_object.add('base', [], constants_string)


def _add_grounding_rules(predicates, control_objects):
    rules = []
    external = '_atom_to_be_released'

    for predicate in predicates:
        epistemic_term = predicate.atom.term
        term = epistemic_term.name.replace('aux_', '') \
                                  .replace('not_', '').replace('sn_', '-')

        if epistemic_term.arguments:
            epistemic_arguments = []
            epistemic_arguments_counter = len(epistemic_term.arguments)

            for index in range(1, epistemic_arguments_counter+1):
                epistemic_arguments.append(('X%d' % index))
            epistemic_arguments = (', ').join(epistemic_arguments)
            rules.append('%s(%s) :- %s(%s), %s.' %
                         (epistemic_term.name, epistemic_arguments,
                          term, epistemic_arguments, external))
        else:
            rules.append('%s :- %s, %s.' % (epistemic_term.name, term, external))

    for control_object in control_objects:
        control_object.add('base', [], '#external %s.' % external)
        control_object.add('base', [], '\n'.join(rules))


def _preprocess(ast, control_objects, predicates, k14):
    if ast.type == clingo.ast.ASTType.Rule:
        preprocessed_body = []
        for body_literal in ast.body:
            if body_literal.atom.type == clingo.ast.ASTType.TheoryAtom:
                theory_term = body_literal.atom.elements[0].tuple[0]
                theory_element = theory_term.elements[0]
                aux_name = 'aux_'
                for operator in theory_element.operators:
                    if operator == '~':
                        aux_name += 'not_'
                    elif operator == '-':
                        aux_name += 'sn_'
                if theory_element.term.type == clingo.ast.ASTType.Symbol:
                    symbol_name = theory_element.term.symbol.name
                    symbol_arguments = theory_element.term.symbol.arguments
                elif theory_element.term.type == clingo.ast.ASTType.TheoryFunction:
                    symbol_name = theory_element.term.name
                    symbol_arguments = [symbol_argument.elements[0].term
                                        for symbol_argument in theory_element.term.arguments]

                sign = body_literal.sign
                if (not k14) and (body_literal.sign == clingo.ast.Sign.NoSign):
                    sign = clingo.ast.Sign.DoubleNegation

                body_literal = clingo.ast.Literal(body_literal.location, sign,
                                                  clingo.ast.SymbolicAtom(
                                                      clingo.ast.Function(body_literal.location,
                                                                          aux_name+symbol_name,
                                                                          symbol_arguments, False)))
                preprocessed_body.append(body_literal)
                predicates.append(body_literal)

                if k14:
                    if ('not_' not in aux_name) and (body_literal.sign != clingo.ast.Sign.Negation):
                        if 'sn_' in aux_name:
                            aux_body_literal = clingo.ast.Literal(
                                body_literal.location, body_literal.sign,
                                clingo.ast.SymbolicAtom(
                                    clingo.ast.UnaryOperation(
                                        body_literal.location,
                                        clingo.ast.UnaryOperator.Minus,
                                        clingo.ast.Function(body_literal.location,
                                                            symbol_name,
                                                            symbol_arguments, False))))
                        else:
                            aux_body_literal = clingo.ast.Literal(
                                body_literal.location, body_literal.sign,
                                clingo.ast.SymbolicAtom(
                                    clingo.ast.Function(body_literal.location,
                                                        symbol_name,
                                                        symbol_arguments, False)))
                        preprocessed_body.append(aux_body_literal)
            else:
                preprocessed_body.append(body_literal)

        rule = clingo.ast.Rule(ast.location, ast.head, preprocessed_body)
        for control_object in control_objects:
            with control_object.builder() as builder:
                builder.add(rule)
    else:
        for control_object in control_objects:
            with control_object.builder() as builder:
                builder.add(ast)


def parse(input_files, constants, k14):
    candidates_gen = clingo.Control(['0', '--project'])
    candidates_test = clingo.Control(['0'])

    predicates = []
    for input_file in input_files:
        with open(input_file, 'r') as program:
            clingo.parse_program(program.read(),
                                 lambda ast: _preprocess(ast, [candidates_gen, candidates_test],
                                                         predicates, k14))
    _add_grounding_rules(predicates, [candidates_gen, candidates_test])

    if constants:
        _add_const(constants, [candidates_gen, candidates_test])

    candidates_gen.ground([('base', [])])
    candidates_test.ground([('base', [])])

    k_signatures = [(name, arity, positive)
                    for (name, arity, positive) in candidates_gen.symbolic_atoms.signatures
                    if 'aux_' in name]

    epistemic_atoms = {}
    for control_object in [candidates_gen, candidates_test]:
        with control_object.backend() as backend:
            for (name, arity, positive) in k_signatures:
                for atom in candidates_gen.symbolic_atoms.by_signature(name, arity):
                    backend.add_rule([atom.literal], [], True)

                    epistemic_symbol = atom.symbol
                    name = epistemic_symbol.name.replace('aux_', '')
                    positive = True
                    if 'sn_' in epistemic_symbol.name:
                        name = name.replace('sn_', '')
                        positive = False
                    if 'not_' in epistemic_symbol.name:
                        name = name.replace('not_', '')
                    epistemic_atoms.update(
                        {epistemic_symbol: clingo.Function(name, epistemic_symbol.arguments,
                                                           positive)})

        control_object.cleanup()

    with candidates_gen.backend() as backend:
        for epistemic, atom in epistemic_atoms.items():
            atom_lit = backend.add_atom(atom)
            if 'not_' not in epistemic.name:
                atom_lit = 0-atom_lit
            backend.add_rule([], [backend.add_atom(epistemic), atom_lit], False)

    candidates_gen.add('projection', [], _generate_projection_directives(k_signatures))
    candidates_gen.ground([('projection', [])])

    return candidates_gen, candidates_test, epistemic_atoms
