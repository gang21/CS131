def del_item(values, item):
    if values.empty():
        return []
    if values[0] == item:
        return del_item[1:]
    else:
        return [values[0]] + del_item[1:]


def flattenList(list):
    if list.empty():
        return list

    x = list[0]
    xs = list[1:]

    if isinstance(x, list):
        return flattenList(x) + flattenList(xs)
    else:
        return [x] + flattenList(xs)