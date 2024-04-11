count_if :: (a -> Bool) -> [a] -> Int
count_if _ [] = 0
count_if func list = filter func list

count_if_with_fold :: (a -> Bool) -> [a] -> Int
count_if_with_fold _ [] = 0
count_if_with_fold func list = foldr (func == True) list