class Postprocessor:

    def __init__(self, candidates_test, show_signatures):
        self._candidates_test = candidates_test
        self._show_signatures = show_signatures

    def postprocess(self, model, assumptions):
        symbols = []
        if assumptions:
            if self._show_signatures:
                show_atoms = []
                for (name, arity, positive) in self._show_signatures:
                    show_atoms += [atom.symbol for atom in
                                   self._candidates_test.symbolic_atoms.by_signature(
                                    name, arity, positive)]

                self._candidates_test.configuration.solve.enum_mode = 'cautious'
                with self._candidates_test.solve(yield_=True, assumptions=assumptions) \
                        as candidates_test_handle:
                    *_, cautious_model = candidates_test_handle
                    k_atoms = [atom for atom in show_atoms
                               if atom in cautious_model.symbols(atoms=True)]

                symbols = [Symbol(atom.name, atom.arguments, True, EpistemicSign.NoSign
                           if atom.positive else EpistemicSign.StrongNegation)
                           for atom in k_atoms]
            else:
                symbols = [Symbol(atom.name.replace('aux_', '').replace('sn_', '')
                           .replace('not_', ''), atom.arguments, True,
                           EpistemicSign.BothNegations if 'not_sn_' in atom.name else
                           EpistemicSign.StrongNegation if 'sn_' in atom.name else
                           EpistemicSign.Negation if 'not_' in atom.name else
                           EpistemicSign.NoSign) for atom in model]

        return Model(symbols, self._candidates_test, assumptions)


class Model:

    def __init__(self, symbols, control, assumptions):
        self.symbols = symbols
        self.control = control
        self.assumptions = assumptions

    def __repr__(self):
        return ' '.join(map(str, sorted(self.symbols)))

    def __eq__(self, other):
        return self.symbols == other.symbols

    def __lt__(self, other):
        return self.symbols < other.symbols

    def get_answer_sets(self, max_answer_sets):
        count = 0
        self.control.configuration.solve.enum_mode = 'auto'
        with self.control.solve(yield_=True, assumptions=self.assumptions) \
                as control_handle:
            for answer_set in control_handle:
                count += 1
                yield AnswerSet(answer_set.symbols(atoms=True))
                if count == max_answer_sets:
                    break


class Symbol:

    def __init__(self, name, arguments, sign, epistemic_sign):
        self.name = name
        self.arguments = arguments
        self.sign = '' if sign else 'not '
        self.epistemic_sign = epistemic_sign

    def __repr__(self):
        arguments = f'({", ".join([str(argument) for argument in self.arguments])})' \
            if self.arguments else ''

        return f'{self.sign}&k{{ {self.epistemic_sign}{self.name}{arguments} }}'

    def __eq__(self, other):
        return self.name == other.name and self.arguments == other.arguments \
            and self.sign == other.sign and self.epistemic_sign == other.epistemic_sign

    def __lt__(self, other):
        return (self.epistemic_sign, self.name, self.arguments) \
            < (other.epistemic_sign, other.name, other.arguments)


class AnswerSet:

    def __init__(self, answer_set):
        self.answer_set = answer_set

    def __repr__(self):
        return ' '.join(filter(lambda x: "aux_" not in x, map(str, sorted(self.answer_set))))


class _EpistemicNoSign:

    def __repr__(self):
        return ''

    def __lt__(self, other):
        return False


class _EpistemicStrongNegation:

    def __repr__(self):
        return '-'

    def __lt__(self, other):
        return other == EpistemicSign.NoSign


class _EpistemicNegation:

    def __repr__(self):
        return '~ '

    def __lt__(self, other):
        return other in [EpistemicSign.NoSign, EpistemicSign.StrongNegation]


class _EpistemicBothNegations:

    def __repr__(self):
        return '~ -'

    def __lt__(self, other):
        return True


class EpistemicSign:

    NoSign = _EpistemicNoSign()
    Negation = _EpistemicNegation()
    StrongNegation = _EpistemicStrongNegation()
    BothNegations = _EpistemicBothNegations()
