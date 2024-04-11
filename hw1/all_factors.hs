all_factors :: Integer -> [Integer]
all_factors num = [x | x <- [1..num], y <- [1..num], x*y == num]

perfect_number = [perf | perf <- [1..], sum(init(all_factors(perf))) == perf]