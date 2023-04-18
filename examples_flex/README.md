Example scripts/scenarios to generate a complete set of FLEX test products. When run in this order:

./generate_aux.sh
./generate_raw.sh
./prep_joborders.sh #(create joborder files from  templates)
./level0_step1.sh JobOrder.1.xml
./level0_step2.sh JobOrder.2.xml
./level0_step3.sh JobOrder.3.xml

The 'workspace/' directory should now be filled. Note that for step 2, input products come from the 'temp' directory.

