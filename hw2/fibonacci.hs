fib 0 = 1
fib 1 = 1
fib num = (fib (num-1)) + (fib (num-2))

fib n = 
    let 
        helper i a b = 
            if i == num
                then b 
            else helper (i + 1) b (a + b)
        helper 0 0 1


--currying problem
f g h i = i h g
g -> h -> (i1 -> i2 -> o) -> o
g -> h -> (h -> g -> o) -> o

f :: t1 -> t2 -> (t2 -> t1 -> t3) -> t3

a -> b -> c --is the same as
(a -> b) -> c

-- homework 1 review Q5
count_occurrences :: [Integer] -> [Integer] -> Integer
count_occurrences [] = 1
count_occurrences _ [] = 0

-- reversing a list
rev [] = []
rev (x:xs) = foldr x : xs