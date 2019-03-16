import glob
import os
import re


def replace_keep_case(word, replacement, text):
    def func(match):
        g = match.group()
        if g.islower(): return replacement.lower()
        if g.istitle(): return replacement.title()
        if g.isupper(): return replacement.upper()
        return replacement
    return re.sub(word, func, text, flags=re.I)


if __name__ == '__main__':
    dir_ = os.path.join(
        os.getcwd(),
        'budget/templates/budget'
    )

    ##########################
    to_be_replaced = 'account'
    new = 'statement'
    ##########################

    files = glob.glob(f'{dir_}/{to_be_replaced}-*')

    for path in files:
        # Read bank file
        with open(path) as f:
            s = f.read()

        # Replace references
        s = replace_keep_case(to_be_replaced, new, s)

        # Write new account file
        new_path = path.replace(to_be_replaced, new)
        with open(new_path, 'w+') as f:
            f.write(s)
