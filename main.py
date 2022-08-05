from ast import operator
from curses import has_key
from logging import exception
from re import I, match
from sys import stderr, argv
from timeit import default_timer

STRING = "string"
SYMBOL = "symbol"
PUNCTUATION = "punctuation"
OPERATOR = "operator"
NUMBER = "number"
STOP = "stop"
KEYWORD = "keyword"

RULE_DECLARATION = "rule declaration"
ASSIGNMENT = "assignment"
OPERATION = "operation"
CALL = "call"
FUNCTION = "function"
COMMENT = "comment"


keyword_list = ("goto", "label")

mem = {}
defaultmem = 0
lines = []
currentline = 0
file = None
labels = {}
functions = []
variables = {}
n_open = 0

def lexer(src):
    # tokens are
    #     - symbols (var names)
    #     - strings : "str"
    #     - numbers (0-9)
    #     - special punctuation :  =;(),{}#
    #     - operator (+, -, *, /)
    tokenlist = []
    i=0
    while i < len(src):
        c = src[i]
        # print(c)
        if c in " \n\t":
            pass #ignore withespace
        elif c in "\"":
            word = ""#match("\w*", src[i+1:])
            i += 1
            c = src[i]
            while c != "\"":
                # print(i, src, end="")
                word = word + c
                i += 1
                c = src[i]

            if word != "":
                tokenlist.append((STRING, word))
        elif c in "=;(),{}#":
            if c == ";":
                tokenlist.append((STOP, c))
            else:
                tokenlist.append((PUNCTUATION, c))
        elif c in "+-*/":
            tokenlist.append((OPERATOR, c))
        elif match("[0-9]", c):
            word = "" + c
            i += 1
            c = src[i]
            while c in "0123456789":
                # print(c)
                word += c
                i += 1
                c = src[i]
            if word != "":
                tokenlist.append((NUMBER, word))
            i -= 1
        elif match("[_a-zA-Z]", c):
            word = match("\w*", src[i:])
            if word is not None:
                if word[0] in keyword_list:
                    tokenlist.append((KEYWORD, word[0]))
                else:
                    tokenlist.append((SYMBOL, word[0]))
                i += len(word[0]) - 1 # because we still add 1 at the end of the loop

        else:
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid character")

        i += 1

    return tokenlist

def _scan(first_char, chars, allowed):
    l = len(chars)
    ret = chars[first_char]
    first_char += 1
    while first_char < l and chars[first_char] is not None and match(allowed, chars[first_char]):
        ret += chars[first_char]
        first_char += 1
    return ret
	
def find(src, token):
    for i in range(len(src)):
        t = src[i]
        if token == t:
            return i
    
    return -1

def findany(src, tokentype):
    for i in range(len(src)):
        t = src[i]
        if tokentype == t[0]:
            return i
    
    return -1

def parse(src):
    global index
    index = 0
    # print(src)
    return next_expression(src, None, "")
    tree = []

    i = find(src, (OPERATOR, "+"))
    l = len(src)

    if len(src) == 1: #just a variable or a string
        if (src[0][0] not in (SYMBOL, STRING, NUMBER)):
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid syntax", file=stderr)
            return None
        return tuple(src[0])



    #rule declaration
    if src[0][0] == SYMBOL and src[0][1] == "rule":
        if (l < 4):
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid rule declaration", file=stderr)
            return None
        index = find(src, (PUNCTUATION, ":"))
        if index in (-1, 0, 1, l-1):
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid rule declaration", file=stderr)
            return None

        tree.append((RULE_DECLARATION, parse(src[1:index]), parse(src[index+1:])))
        if tree[-1][1] is None or tree[-1][2] is None:
            return None


    #variable assigniation
    elif src[0][0] == SYMBOL and src[1] == (PUNCTUATION, "="):
        if (l < 3):
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid variable declaration", file=stderr)
            return None
        index = find(src, (PUNCTUATION, "="))
        if index != 1:
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid variable declaration", file=stderr)
            return None

        tree.append((VARIABLE_DECLARATION, src[0][1], parse(src[index+1:])))
        # print(tree[-1])
        if tree[-1][2] is None:
            return None


    #operation
    elif i > 0 and i < l-1:
        if (l < 3):
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid operation", file=stderr)
            return None

        index = findany(src, OPERATOR)

        tree.append((OPERATION, src[index], parse(src[:i]), parse(src[i+1:])))
        # print(tree[-1])
        if tree[-1][1] is None or tree[-1][2] is None:
            return None

    else:
        print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid syntax", file=stderr)
        return None




## WARNING !! peut etre qu'il faudra enlenver le [0] si ca cause des problemes
    return tuple(tree[0])


index = 0
def next_expression(tokens, prev, stop_at):
    global index
    # print(tokens, index)
    # print(index, tokens[index])
    if fail_if_at_end(tokens, stop_at):
        # print("enenenend")
        return prev
    typ, value = tokens[index]
    # print(typ, value)
    if typ == STOP:
        # print(prev)
        return prev
    # print("plizze", typ, value)
    index += 1
    if typ in (NUMBER, STRING, SYMBOL) and (prev is None):
        return next_expression(tokens, (typ, value), stop_at)
    elif typ == KEYWORD:
        nxt = next_expression(tokens, None, stop_at)
        e = next_expression(tokens, (KEYWORD, value, nxt), stop_at)
        if value == "label":
            # print(tokens)
            if len(tokens) < 2:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nExpected label name", file=stderr)
                return None
            elif len(tokens) > 2:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nOnly one label name can be specified", file=stderr)
                return None
            else:
                labels[tokens[1][1]] = currentline
        return e
    elif typ == OPERATOR:
        # print(prev)
        nxt = next_expression(tokens, None, stop_at)
        # print(nxt)
        return next_expression(tokens, (OPERATION, value, prev, nxt), stop_at)
    elif typ == PUNCTUATION:
        # print(index)
        if value == "(":
            args = multiple_expressions(tokens, ",", ")")
            return next_expression(tokens, (CALL, prev, args), stop_at)
        elif value == "{":
            params = parameters_list()
            body = multiple_expressions(tokens, ";", "}")
            if body is None:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\Invalid syntax", file=stderr)
            return next_expression(tokens, (FUNCTION, params, body), stop_at)
        elif value == "=":
            if prev[0] != SYMBOL:
                raise Exception("You can only assign to a symbol.")
            nxt = next_expression(tokens, None, stop_at)
            return next_expression(tokens, (ASSIGNMENT, prev, nxt), stop_at)
        elif value == "#":
            return (COMMENT, )
    else:
        raise Exception("Unexpected token: " + str((typ, value)))

def parameters_list():
    return None

def fail_if_at_end(tokens, end):
    if index == len(tokens):
        return True
    return index >= len(tokens)  or tokens[index][1] in end

def multiple_expressions(tokens, sep, end):
    global index
    # print("multiple")
    if fail_if_at_end(tokens, end):
        # print("oh no")
        return None
    ret = []
    typ, value = tokens[index]
    if value in end:
        index += 1
    else:
        arg_parser = tokens
        stopat = (sep, end)
        while value not in end:   
            # ind = index
            # index = 0
            # print("next")
            p = next_expression(arg_parser, None, stopat)
            # print("finished")
            # index = ind
            if p is not None:
                ret.append(p)
            typ, value = tokens[index]
            if fail_if_at_end(tokens, end):
                # print("oh no bis")
                break
                return None
            index += 1
    # print(ret)
    index += 1
    return tuple(ret)

def evaluate(tree):
    global currentline, mem, defaultmem
    if tree is None:
        return None
    if type(tree[0]) == tuple:
        # print(tree)
        return evaluate(tree[0])
    # print([tree])
    if tree[0] == SYMBOL:
        if tree[1] in variables:
            return variables[tree[1]]
        elif tree[1] in labels:
            return tree[1]
        else:
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nUnknown symbol \"{tree[1]}\"", file=stderr)
            return None
    

    elif tree[0] in (STRING, NUMBER):
        return tree[1]

    elif tree[0] == KEYWORD:
        if tree[1] == "goto":
            # print(tree)
            if len(tree) < 3:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nNo label was specified for goto", file=stderr)
                return None
            elif len(tree) > 3:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nOnly one label can be given to goto", file=stderr)
                return None
            else:
                currentline = labels[tree[2][1]]
            return currentline
        elif tree[1] == "label":
            if len(tree) < 3:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nExpected label name", file=stderr)
                return None
            elif len(tree) > 3:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nOnly one label name can be specified", file=stderr)
                return None
            else:
                labels[tree[2][1]] = currentline
            return currentline


    elif tree[0] == OPERATION:
        val1 = evaluate(tree[2])
        val2 = evaluate(tree[3])
        # print(val1, val2)
        operator = tree[1]
        if val1 is None or val2 is None or operator is None:
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\Invalid operation", file=stderr)
            return None
        if operator not in "+-*/":
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nUnknown operator \"{operator}\"", file=stderr)
            return None
        elif operator == '+':
            return str(int(val1) + int(val2))
        elif operator == '-':
            return str(int(val1) - int(val2))
        elif operator == '*':
            return str(int(val1) * int(val2))
        elif operator == '/':
            return str(int(val1) // int(val2))
    
    elif tree[0] == CALL:
        # print(f"calling func {tree[1][1]}")
        args = [evaluate(t) for t in tree[2]]
        
        if tree[1] is None:
            if len(args) == 1:
                return args[0]
            else:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid syntax", file=stderr)

        #builtin funcs
        if tree[1][1] == "print":
            # print(args)
            for i in range(len(args)):
                arg = args[i]
                if i == len(args)-1:
                    print(arg, end="")
                else:
                    print(arg, end=" ")
            return currentline
        elif tree[1][1] == "max":
            return max(args)
        elif tree[1][1] == "char":
            if (len(args) != 1):
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\Function \"{tree[1][1]}\" expected 1 argument, {len(args)} were given", file=stderr)
            return chr(int(args[0]))
        elif tree[1][1] == "input":
            # if len(args) != 0:
            #     print(f"ERROR at line {currentline}\n{lines[currentline-1]}\Function \"{tree[1][1]}\" expected 0 argument, {len(args)} were given", file=stderr)
            return ord(input()[0])
        elif tree[1][1] == "jump":
            # print(tree)
            if len(args) != 2:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid jump statement", file=stderr)
                return None
            else:
                # print(tree)
                e = evaluate(tree[2][1])
                # print(e)
                if type(e) == str and len(e) > 0:
                    e = int(e)
                # print("e =", e, type(e))
                if e:
                    currentline = labels[tree[2][0][1]]
                return currentline
        elif tree[1][1] == "getmem":
            if len(args) != 1:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nFunction getmem expected 1 argument, {len(args)} were given", file=stderr)
                return None
            else:
                ind = int(args[0])
                try:
                    # print("ind = ", ind)
                    return str(mem[ind])
                except KeyError:
                    return str(defaultmem)
        elif tree[1][1] == "setmem":
            if len(args) != 2:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nFunction setmem expected 2 argument, {len(args)} were given", file=stderr)
                return None
            else:
                if (int(args[1])):
                    mem[int(args[0])] = str(args[1])
                elif int(args[0]) in mem.keys():
                    mem.pop(int(args[0]))
                # print(mem[args[0]])
                return currentline
        elif tree[1][1] == "resetmem":
            if len(args) != 1:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nFunction resetmem expected 1 argument, {len(args)} were given", file=stderr)
                return None
            else:
                mem = {}
                defaultmem = int(args[0])
                return currentline

        else:
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nUnokwn function \"{tree[1][1]}\"", file=stderr)
            return None

    elif tree[0] == COMMENT:
        return currentline

    else:
        print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid syntax", file=stderr)
        return None


def interprete(file):
    global currentline, functions, variables
    big_tree = []
    for line in file:
        currentline += 1
        lines.append(line)
        line = lexer(line)
        if (len(line) <= 0):
            big_tree.append(None)
            continue
        
        # print(line)
        tree = parse(line)
        # print(tree)
        if tree is None:
            print("abandon")
            return None
        big_tree.append(tree)
        # if tree[0] == RULE_DECLARATION:
        #     rules.append((evaluate(tree[1]), evaluate(tree[2])))
        #     if None in (rules[-1][0], rules[-1][1]):
        #         return None
        # elif tree[0] == VARIABLE_DECLARATION:
        #     # if tree[1] == "main":
        #     #     variables[tree[1]] = tree[2]
        #     # else:
        #     variables[tree[1]] = evaluate(tree[2])
        #     if variables[tree[1]] is None:
        #         return None
        # else:
        #     print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid syntax", file=stderr)
        #     return None
    

    # print(big_tree)
    print(labels)
    # print(lines)

    srclen = len(big_tree)
    currentline = 1
    while currentline <= srclen:
        # print("line =", currentline)
        tree = big_tree[currentline-1]
        if tree is None:
            currentline += 1
            continue

        if len(tree) < 1:
            print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nInvalid syntax", file=stderr)
            return None
        

        if tree[0] == ASSIGNMENT:
            if tree[1][0] != SYMBOL:
                print(f"ERROR at line {currentline}\n{lines[currentline-1]}\nCan only assign to variables", file=stderr)
                return None
            
            variables[tree[1][1]] = evaluate(tree[2])
            if variables[tree[1][1]] == None:
                return None

        else:
            if evaluate(tree) is None:
                return None
            
        # print(currentline, mem)
        currentline += 1


def main():
    global file
    ok = 0
    for name in argv:
        if name[-4:] == ".piz":
            ok = 1
            try:
                file = open(name, "r")
            except Exception as e:
                print(e)
                return None
            break
    if not ok:
        print("ERROR no file specified")
        return None
    interprete(file)
    file.close()

if __name__ == "__main__":
    main()