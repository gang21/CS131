reflect :: Integer -> Integer
reflect 0 = 0
reflect num
    | num < 0 = (-1) + reflect (num+1)
    | num > 0 = 1 + reflect (num-1)