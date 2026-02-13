# The cleanup
I have identified things i want to make a bit nicer - if there are any questions or things you don't agree with, let me know.

## remove old libraries
libraries, pip packages, docker components, docs, scripts that doesnt have any use anymore 

## make the postgress default
right now we can both use local and postgress - lets add a flag in the .env file so we can tell weather to run the vault locally in the folder it is running from in a format like: use_cloue=true for postgress and false for a local vault with a base for being mounted in the folder it is being run from and paths that people can specify things from

## all the shared
if people rename things or add new exercise names, those should be in a general list and when they want to add a new one it should be able to suggest from others who have added to that list eg. if i make a custom exercise it should be added to the list of exercises

## Building it as a product
* eventually this will be a full product being spun up containerized somewhere - lets ensure it is easy to do and will be able to run really cheap
* i think i will try to implement clerk as the login service - lets look into if our solution can support that we will integrate this or if we need to update some radical part of the project eg. database, yaml files
* in the sales pitch - lets try to also emply that this is apple notes or onenote without you having to categorize anything 

## check for general optimization points
in this repo, is there something we can do better? i am speaking structure wise, naming wise, database wise - speed and performance is key !

## ensure everything is up to date
docs, libraries etc. ensure it is up to date
