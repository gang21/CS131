count_occurrences :: [Integer] -> [Integer] -> Integer
count_occurrences [] [_] = 1
count_occurrences list1 list2
    | length list1 == 1 && length list2 == 1 && (head list1) == (head list2) = 1
    | length list1 == 1 && length list2 == 1 && (head list1) /= (head list2) = 0
    | length list1 > length list2 = 0
    | list1_first == list2_first = (count_occurrences list1_rest list2_rest) + (count_occurrences list1 list2_rest)
    | otherwise = count_occurrences list1 list2_rest
    where
        list1_first = head list1
        list1_rest = tail list2
        list2_first = head list1
        list2_rest = tail list2
