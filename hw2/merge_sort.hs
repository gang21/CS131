sort :: [Integer] -> [Integer] -> [Interger] 
sort [] [] = []
sort [] list = list
sort list [] = list
sort (x:xs) (y:ys) 
  | x < y = x : sort xs (y:ys)
  | otherwise = y : sort (x:xs) ys

splitHelper [] y z = (y, z)
splitHelper (x:xs) y z = SplitHelpter xs z (x:y)

split l = splitHelper l [] []

merge_sort [] = []
merge_sort [x] = x
merge_sort list = 
    let (x,y) = split length
    in sort (merge_sort x) (merge_sort y)