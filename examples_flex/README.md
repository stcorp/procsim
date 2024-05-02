Example scripts/scenarios to generate a set of FLEX test products. When run in this order:

./generate_aux.sh
./generate_raw.sh
./level0_step1.sh JobOrder.1.xml
./level0_step2.sh JobOrder.2.xml
./level0_step3.sh JobOrder.3.xml

The 'workspace/' directory should now be filled. Note that for step 2, input products come from the 'temp' directory.

The grep_joborder.sh script shows how to (crudely) check that a JobOrder file contains a certain string.


**** No longer working 2024/5/2 ****
