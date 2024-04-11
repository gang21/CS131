import copy
from curses import ERR
from dataclasses import field
from enum import Enum
from pickle import OBJ

from brewparse import parse_program
from env_v4 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev4 import Closure, Type, Value, Object, create_value, get_printable


class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()
        self.objects = {}

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        # print(ast)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        main_func = self.__get_func_by_name("main", 0)
        if main_func is None:
            super().error(ErrorType.NAME_ERROR, f"Function main not found")
        self.__run_statements(main_func.func_ast.get("statements"))

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        empty_env = EnvironmentManager()
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = Closure(func_def, empty_env)

    def __get_func_by_name(self, name, num_params):
        if name not in self.func_name_to_ast:
            closure_val_obj = self.env.get(name)
            if closure_val_obj is None:
                return None
                # super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
            if closure_val_obj.type() != Type.CLOSURE:
                super().error(
                    ErrorType.TYPE_ERROR, "Trying to call function with non-closure"
                )
            closure = closure_val_obj.value()
            num_formal_params = len(closure.func_ast.get("args"))
            if num_formal_params != num_params:
                super().error(ErrorType.TYPE_ERROR, "Invalid # of args to lambda")
            return closure_val_obj.value()

        candidate_funcs = self.func_name_to_ast[name]
        if num_params is None:
            # case where we want assign variable to func_name and we don't have
            # a way to specify the # of arguments for the function, so we generate
            # an error if there's more than one function with that name
            if len(candidate_funcs) > 1:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Function {name} has multiple overloaded versions",
                )
            num_args = next(iter(candidate_funcs))
            closure = candidate_funcs[num_args]
            return closure

        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]

    def __run_statements(self, statements, calling_obj=None):
        # print("__run_statements: ", calling_obj)
        self.env.push()
        for statement in statements:
            if self.trace_output:
                print(statement)
            status = ExecStatus.CONTINUE
            if statement.elem_type == InterpreterBase.FCALL_DEF:
                self.__call_func(statement, calling_obj)
            elif statement.elem_type == "=":
                self.__assign(statement, calling_obj)
            elif statement.elem_type == InterpreterBase.RETURN_DEF:
                status, return_val = self.__do_return(statement, calling_obj)
            elif statement.elem_type == Interpreter.IF_DEF:
                status, return_val = self.__do_if(statement, calling_obj)
            elif statement.elem_type == Interpreter.WHILE_DEF:
                status, return_val = self.__do_while(statement, calling_obj)
            elif statement.elem_type == InterpreterBase.MCALL_DEF:
                self.__call_method(statement, calling_obj)

            if status == ExecStatus.RETURN:
                self.env.pop()
                return (status, return_val)

        self.env.pop()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)


    def __call_func(self, call_ast, calling_obj=None):
        func_name = call_ast.get("name")
        # print("--------------------", func_name, "--------------------")
        c = self.env.get("c")
        # print(c.value().func_ast)
        # self.env.print_env()
        if func_name == "print":
            return self.__call_print(call_ast, calling_obj)
        if func_name == "inputi":
            return self.__call_input(call_ast, calling_obj)

        actual_args = call_ast.get("args")
        target_closure = self.__get_func_by_name(func_name, len(actual_args))
        # print("TARGET CLOSURE: ", target_closure.func_ast)
        if target_closure == None:
            super().error(ErrorType.NAME_ERROR, f"Function {func_name} not found")
        if target_closure.type != Type.CLOSURE:
            super().error(ErrorType.TYPE_ERROR, f"Function {func_name} is changed to non-function type.")
        target_ast = target_closure.func_ast
        # print("TARGET AST: ", target_ast)
        new_env = {}
        self.__prepare_env_with_closed_variables(target_closure, new_env)
        self.__prepare_params(target_ast,call_ast, new_env)
        self.env.push(new_env)
        # print("************* NEW ENV****************")
        # self.env.print_env()
        # print("************* NEW ENV****************")
        _, return_val = self.__run_statements(target_ast.get("statements"))
        self.env.pop()
        return return_val

    def __prepare_env_with_closed_variables(self, target_closure, temp_env):
        for var_name, value in target_closure.captured_env:
            # print(var_name, ": ", value.value())
            if value.type() == Type.OBJECT or value.type() == Type.CLOSURE:
                continue    # pass by reference, not copying to new environment
            # Updated here - ignore updates to the scope if we
            #   altered a parameter, or if the argument is a similarly named variable
            temp_env[var_name] = value


    def __prepare_params(self, target_ast, call_ast, temp_env, calling_obj=None):
        # print(target_ast.elem_type)
        actual_args = call_ast.get("args")
        formal_args = target_ast.get("args")
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {target_ast.get('name')} with {len(actual_args)} args not found",
            )

        for formal_ast, actual_ast in zip(formal_args, actual_args):
            if formal_ast.elem_type == InterpreterBase.REFARG_DEF:
                result = self.__eval_expr(actual_ast, calling_obj=calling_obj)
            else:
                result = copy.deepcopy(self.__eval_expr(actual_ast, calling_obj=calling_obj))

            if actual_ast.get("name") in self.objects:
                original = self.objects[actual_ast.get("name")]
                if formal_ast.elem_type == InterpreterBase.REFARG_DEF:
                    self.objects[formal_ast.get("name")] = original
                else:
                    self.objects[formal_ast.get("name")] = copy.deepcopy(original)
            arg_name = formal_ast.get("name")
            temp_env[arg_name] = result

    def __call_print(self, call_ast, calling_obj=None):
        # self.env.print_env()
        output = ""
        for arg in call_ast.get("args"):
            result = self.__eval_expr(arg, calling_obj=calling_obj)  # result is a Value object
            printable = get_printable(result)
            if printable is None:
                super().error(
                    ErrorType.NAME_ERROR, f"Value to print does not exist"
                )
            output = output + printable
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_input(self, call_ast, calling_obj=None):
        args = call_ast.get("args")
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0], calling_obj=calling_obj)
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if call_ast.get("name") == "inputi":
            return Value(Type.INT, int(inp))
        if call_ast.get("name") == "inputs":
            return Value(Type.STRING, inp)

    def __assign(self, assign_ast, calling_obj=None):
        var_name = assign_ast.get("name")
        if var_name == "this":
            var_name = calling_obj
        # checking for object property/method assignment
        if "." in var_name:
            # print(var_name)
            self.__add_to_obj(var_name, assign_ast, calling_obj)
            return
        src_value_obj = copy.copy(self.__eval_expr(assign_ast.get("expression"), var_name, calling_obj=calling_obj))
        target_value_obj = self.env.get(var_name)
        self.env.set(var_name, src_value_obj)

        print("var name: ", var_name)
        print("tar val obj: ", target_value_obj)
        # removing object reference if it no longer exists
        if var_name in self.objects.keys() and src_value_obj.type() != Type.OBJECT:
            del self.objects[var_name]
        # elif target_value_obj is not None and target_value_obj.type() == Type.OBJECT:
        #     self.objects[var_name] = target_value_obj.value()

        # # assigning objects to each other
        # if target_value_obj is not None and target_value_obj.type() == Type.OBJECT:
        #     self.objects[var_name] = target_value_obj.value()

        if target_value_obj is None:
            if src_value_obj.type() == Type.OBJECT:
                print(self.objects)
                # del self.objects[var_name]
                print("src val obj: ",src_value_obj)
                self.objects[var_name] = src_value_obj.value()
            self.env.set(var_name, src_value_obj)
        else:
            # if target_value_obj.type() == Type.OBJECT:
            #     self.objects[var_name] = target_value_obj.value()
            # if a close is changed to another type such as int, we cannot make function calls on it any more 
            if target_value_obj.t == Type.CLOSURE and src_value_obj.t != Type.CLOSURE:
                target_value_obj.v.type = src_value_obj.t
            target_value_obj.set(src_value_obj)
        # self.env.print_env()

    def __add_to_obj(self, var_name, expr_ast, calling_obj=None):
        n = var_name.split(".")
        # print("EXPR AST: ", expr_ast)
        # self.env.print_env()
        obj_name = n[0]
        field_name = n[1]
        # print(obj_name)
        if(obj_name == "this"):
            obj_name = calling_obj
        if obj_name not in self.objects:
            # print("HERE HERE HERE")
            # check in list of vars first
            if self.env.get(obj_name) is None: 
                super().error(
                    ErrorType.NAME_ERROR, f"Object {obj_name} not found"
                )
            potential_obj = self.env.get(obj_name).value()
            val = self.__eval_expr(expr_ast.get("expression"), calling_obj=calling_obj)
            if (val.type() == Type.CLOSURE) or (val.value() == Value and val.value().type() == Type.CLOSURE):  # method
                # print("METHOD!!")
                num_args = len(val.value().func_ast.get("args"))
                if field_name not in potential_obj.methods.keys():
                    potential_obj.methods[field_name] = {}
                potential_obj.methods[field_name][num_args] = val
                return Value(Type.OBJECT, potential_obj)
            else:   # property
                potential_obj.properties[field_name] = val
                # print("PROPS: ", potential_obj.properties)
                return Value(Type.OBJECT, potential_obj)
        # get obj
        obj = self.objects[obj_name]
        val = self.__eval_expr(expr_ast.get("expression"), calling_obj=calling_obj)
        if field_name == "proto":
            if (val.type() != Type.OBJECT):
                if (val.value() == Interpreter.NIL_DEF):
                    obj.proto = None
                else:
                    super().error(
                        ErrorType.TYPE_ERROR, f"{val} is not an Object, cannot be assigned to proto field"
                    )
            obj.proto = val
        if (val.type() == Type.CLOSURE) or (val.value() == Value and val.value().type() == Type.CLOSURE):  # method
            # print("METHOD!!")
            num_args = len(val.value().func_ast.get("args"))
            if field_name not in obj.methods.keys():
                obj.methods[field_name] = {}
            obj.methods[field_name][num_args] = val
            return Value(Type.OBJECT, obj)
        else:   # property
            obj.properties[field_name] = val
            # print("PROPS: ", obj.properties)
            return Value(Type.OBJECT, obj)     

    def __eval_expr(self, expr_ast, var_name=None, calling_obj=None):
        if expr_ast.elem_type == InterpreterBase.NIL_DEF:
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_DEF:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_DEF:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_DEF:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.VAR_DEF:
            if "." in expr_ast.get("name"):
                return self.__get_obj_val(expr_ast, calling_obj)
            return self.__eval_name(expr_ast)
        if expr_ast.elem_type == InterpreterBase.FCALL_DEF:
            return self.__call_func(expr_ast, calling_obj=calling_obj)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast, calling_obj=calling_obj)
        if expr_ast.elem_type == Interpreter.NEG_DEF:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_DEF:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)
        if expr_ast.elem_type == Interpreter.LAMBDA_DEF:
            return Value(Type.CLOSURE, Closure(expr_ast, self.env))
        if expr_ast.elem_type == Interpreter.OBJ_DEF:
            return self.__create_obj(expr_ast, var_name)
        if expr_ast.elem_type == Interpreter.MCALL_DEF:
            return self.__call_method(expr_ast)

    def __create_obj(self, obj_ast, obj_name):
        obj = Object()
        self.objects[obj_name] = obj
        return Value(Type.OBJECT, obj)

    def __get_obj_val(self, expr_ast, calling_obj=None):
        # print("GET OBJ VAL AST: ", expr_ast)
        var = expr_ast.get("name")
        n = var.split(".")
        obj_name = n[0]
        field_name = n[1]
        if obj_name == "this" and calling_obj is not None:
            obj_name = calling_obj
        if obj_name not in self.objects.keys():
            if self.env.get(obj_name) is not None:
                super().error(
                    ErrorType.TYPE_ERROR, f"dot operator used on non-object {obj_name}"
                )
            super().error(
                ErrorType.NAME_ERROR, f"Object {obj_name} not found"
            )
        obj = self.objects[obj_name]

        # checking for proto object
        if field_name == "proto":
            # print("PROTO OBJECT: ", obj.proto)
            return obj.proto
        if field_name not in obj.properties.keys():
            # check proto object
            potential_proto = self.__process_proto(obj_name, field_name, num_args=None, calling_obj=calling_obj)
            if potential_proto is not None:
                return potential_proto
            super().error(
                ErrorType.NAME_ERROR, f"Object property {field_name} not found"
            )
        
        # print(obj.properties[field_name])
        return obj.properties[field_name]

    def __call_method(self, method_ast, calling_obj=None):
        # print("__call_method: ", calling_obj)
        obj_name = method_ast.get("objref")
        # print("object name: ", obj_name)
        if obj_name == "this":
            obj_name = calling_obj
        if obj_name not in self.objects.keys():
            if self.env.get(obj_name) is not None:
                super().error(
                    ErrorType.TYPE_ERROR, f"{obj_name} is not an object"
                )
            super().error(
                ErrorType.NAME_ERROR, f"Object {obj_name} not found"
            )
        obj = self.objects[obj_name]
        m_name = method_ast.get("name")
        # print("method name: ", m_name)
        num_args = len(method_ast.get("args"))
        # check proto object
        potential_proto = self.__process_proto(obj_name, m_name, num_args=num_args, calling_obj=calling_obj)
        if potential_proto is not None:
            method_closure = potential_proto
        if m_name in obj.methods.keys():
            method_closure = obj.methods[m_name][num_args].value()
        if potential_proto is None and m_name not in obj.methods.keys():
            if m_name in obj.properties.keys():
                super().error(
                    ErrorType.TYPE_ERROR, f"Object property {m_name} cannot be called"
                )
            super().error(
                ErrorType.NAME_ERROR, f"Object method {m_name} not found"
            )
        m_ast = method_closure.func_ast
        new_env = {}
        self.__prepare_env_with_closed_variables(method_closure, new_env)
        self.__prepare_params(m_ast,method_ast, new_env)
        self.env.push(new_env)
        # print("__call_method: ", obj_name)
        _, return_val = self.__run_statements(m_ast.get("statements"), calling_obj=obj_name)
        self.env.pop()
        return return_val

    def __process_proto(self, obj_name, field_or_method, num_args=None, calling_obj=None):
        obj = self.objects[obj_name]
        if obj_name == "this":
            obj = self.objects[calling_obj]
        proto = obj.proto
        if proto is None:
            return None
        proto = obj.proto.value()
        if proto == Interpreter.NIL_DEF:
            return None
        if num_args is None:    # property
            while proto is not None:
                if field_or_method in proto.properties.keys():
                    return proto.properties[field_or_method]
                proto = proto.proto
                if proto is None:
                    return None
                proto = proto.value()
        else:   # method
            while proto is not None:
                if field_or_method in proto.methods.keys():
                    return proto.methods[field_or_method][num_args].value()
                proto = proto.proto
                if proto is None:
                    return None
                proto = proto.value()
                
        return None

    def __eval_name(self, name_ast):
        var_name = name_ast.get("name")
        val = self.env.get(var_name)
        if val is not None:
            return val
        closure = self.__get_func_by_name(var_name, None)
        if closure is None:
            super().error(
                ErrorType.NAME_ERROR, f"Variable/function {var_name} not found"
            )
        return Value(Type.CLOSURE, closure)

    

    def __eval_op(self, arith_ast, calling_obj=None):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"), calling_obj=calling_obj)
        right_value_obj = self.__eval_expr(arith_ast.get("op2"), calling_obj=calling_obj)

        # print("LEFT: ", left_value_obj.value())
        # print("RIGHT: ", right_value_obj.value())


        left_value_obj, right_value_obj = self.__bin_op_promotion(
            arith_ast.elem_type, left_value_obj, right_value_obj
        )

        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)

    # bool and int, int and bool for and/or/==/!= -> coerce int to bool
    # bool and int, int and bool for arithmetic ops, coerce true to 1, false to 0
    def __bin_op_promotion(self, operation, op1, op2):
        if operation in self.op_to_lambda[Type.BOOL]:  # && or ||
            
            # If this operation is still allowed in the ints, then continue
            if operation in self.op_to_lambda[Type.INT] and op1.type() == Type.INT \
                and op2.type() == Type.INT:
                pass
            else:
                if op1.type() == Type.INT:
                    op1 = Interpreter.__int_to_bool(op1)
                if op2.type() == Type.INT:
                    op2 = Interpreter.__int_to_bool(op2)
        if operation in self.op_to_lambda[Type.INT]:  # +, -, *, /
            if op1.type() == Type.BOOL:
                op1 = Interpreter.__bool_to_int(op1)
            if op2.type() == Type.BOOL:
                op2 = Interpreter.__bool_to_int(op2)
        return (op1, op2)

    def __unary_op_promotion(self, operation, op1):
        if operation == "!" and op1.type() == Type.INT:
            op1 = Interpreter.__int_to_bool(op1)
        return op1

    @staticmethod
    def __int_to_bool(value):
        return Value(Type.BOOL, value.value() != 0)

    @staticmethod
    def __bool_to_int(value):
        return Value(Type.INT, 1 if value.value() else 0)

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, t, f, calling_obj=None):
        value_obj = self.__eval_expr(arith_ast.get("op1"), calling_obj=calling_obj)
        value_obj = self.__unary_op_promotion(arith_ast.elem_type, value_obj)

        if value_obj.type() != t:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        return Value(t, f(value_obj.value()))

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )

        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )

        #  set up operations on closures
        self.op_to_lambda[Type.CLOSURE] = {}
        self.op_to_lambda[Type.CLOSURE]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.CLOSURE]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )

        #  set up operations on objects
        self.op_to_lambda[Type.OBJECT] = {}
        self.op_to_lambda[Type.OBJECT]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.OBJECT]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )

    def __do_if(self, if_ast, calling_obj=None):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast, calling_obj=calling_obj)
        if result.type() == Type.INT:
            result = Interpreter.__int_to_bool(result)
        if result.type() != Type.BOOL:
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for if condition",
            )
        if result.value():
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_while(self, while_ast, calling_obj=None):
        cond_ast = while_ast.get("condition")
        run_while = Interpreter.TRUE_VALUE
        while run_while.value():
            run_while = self.__eval_expr(cond_ast, calling_obj=calling_obj)
            if run_while.type() == Type.INT:
                run_while = Interpreter.__int_to_bool(run_while)
            if run_while.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for while condition",
                )
            if run_while.value():
                statements = while_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RETURN:
                    return status, return_val

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast, calling_obj=None):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        value_obj = copy.deepcopy(self.__eval_expr(expr_ast, calling_obj=calling_obj))
        return (ExecStatus.RETURN, value_obj)
