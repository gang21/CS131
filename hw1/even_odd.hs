is_odd :: Integer -> Bool
   | is_odd 1 = True
   | is_odd 3 = True
   | is_odd 5 = True
   | is_odd 7 = True
   | is_odd 9 = True
   | is_odd num = False
    where
        num = head(reverse(show num))


is_even :: Integer -> Bool
is_even num = 
    if num == 0
        then True
    else if num == 1
        then False
    else is_even(num - 2)