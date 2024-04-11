data LinkedList = EmptyList | ListNode Integer LinkedList 
    deriving Show

ll_contains :: LinkedList -> Integer -> Bool
ll_contains EmptyList _ = False
ll_contains (ListNode num1 linked) num2
  | num1 == num2 = True
  | otherwise = ll_contains linked num2

ll_insert :: LinkedList -> ListNode -> Integer -> LinkedList
ll_contains EmptyList node _ = node
ll_contains (ListNode num linked) (ListNode value EmptyList) position 
    | num <= 0 = (ListNode value linked)
    | otherwise = ll_insert linked (ListNode value EmptyList) position-1

