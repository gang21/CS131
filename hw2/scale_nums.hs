scale_nums :: [Integer] -> Integer -> [Integer]
scale_nums [] _ = []
scale_nums list factor = map (*factor) list

only_odds :: [[Integer]] -> [[Integer]]
only_odds list =  [x | x <- list, all odd x]


largest :: String -> String -> String
largest first second = if length first >= length second then first else second 

largest_in_list :: [String] -> String
largest_in_list [] = ""
largest_in_list list = foldl largest (head list) (tail list)