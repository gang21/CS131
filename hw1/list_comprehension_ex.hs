-- [1..][1..][1..]
--pythagorean = [ (x,y,z) | z <-[1..], x <-[1..], y <-[1..], x^2 + y^2 == z^2]

pythagorean :: [(Int, Int, Int)]
pythagorean = [ (x,y,z) | z <- [1..], y <- [1..z], x<-[1..y],  x^2 + y^2 == z^2]
--order matters in this situation
--if not z,y,x, you will get an infinite loop in the inntermost loop