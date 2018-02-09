#!/usr/bin/env python
import os, sys
from time import sleep

if __name__ == "__main__":
    path = sys.argv[1]
    file = open(path, "w")
    counter = 0
    try:

        file.write("habia una vez un"+os.linesep+"barquito chiquitito"+os.linesep+"que no podia navegar")
        while True:
            file.write(str(counter))
            file.flush()
            counter +=1 
            if not counter % 5:
                file.write(os.linesep)
                file.flush()

            if not counter % 20:
                break
            sleep(1)
        file.write("habia una vez un"+os.linesep+"barquito chiquitito"+os.linesep)
        file.flush()
    except KeyboardInterrupt:
        print "exit"
