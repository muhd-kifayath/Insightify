import pickle
print("1.Create a Class\n2.Mark Attendance\n3.Add Name and Detail of a Student\n4.Remove Name and Details of a student\n5. Check Attendance of a Particular Student")
w=int(input("What you want to do? 1, 2, 3, 4 or 5:"))
if w==1:
    def create_class():
        cn=input("Enter name of the class:")
        nc=cn+".dat"
        f=open(nc,'wb')
        n=int(input("Enter no. of students in the class:"))
        std={}
        for i in range (1,n+1):
            admnno=input("Enter Admn no:")
            name=input("Enter name of the student:")
            att={}
            data=[name,att]
            std[admnno]=data
        pickle.dump(std,f)
        f.close()

    create_class()

elif w==2:
    def mark_attendance():
        cn=input("Enter name of the class:")
        nc=cn+".dat"
        f1=open(nc,'rb')
        stud=pickle.load(f1)
        ky=stud.keys()
        f1.close()
        f2=open(nc,'wb')
        nstd={}
        d=input("Enter date in the format DD-MM-YYYY:")
        for j in ky:
            lt=stud[j]
            atd=lt[1]
            print(lt[0],"Present or Absent")
            a=input("Enter:")
            atd[d]=a
            lt[1]=atd
            nstd[j]=lt
        pickle.dump(nstd,f2)
        f2.close()

    mark_attendance()

elif w==3:
    def add_a_student():
        cn=input("Enter name of the class:")
        nc=cn+".dat"
        f3=open(nc,'rb')
        stu=pickle.load(f3)
        ks=stu.keys()
        f3.close()
        f4=open(nc,'wb')
        adno=input("Enter Admn no of new student:")
        nm=input("Enter name of the student:")
        at={}
        dat=[nm,at]
        stu[adno]=dat
        pickle.dump(stu,f4)
        f4.close()

    add_a_student()

elif w==4:
    def remove_a_student():
        cn=input("Enter name of the class:")
        nc=cn+".dat"
        f5=open(nc,'rb')
        sdt=pickle.load(f5)
        f5.close()
        f6=open(nc,'wb')
        ano=input("Enter admn no of the student to be removed:")
        l=sdt[ano]
        n=l[0]
        print("Details of student to be removed:",ano,"&",n)
        k=input("If wrong Enter 'x' to stop:")
        if k=='x' or k=='X':
            print("Start again")
            exit
        
        else:
            sdt.pop(ano)
        pickle.dump(sdt,f6)
        f6.close

    remove_a_student()

elif w==5:
    def attendance_of_particular_student():
        cn=input("Enter name of the class:")
        nc=cn+".dat"
        f7=open(nc,'rb')
        stdt=pickle.load(f7)
        f7.close()
        ano=input("Enter admn no of the student to be searched:")
        L=stdt[ano]
        name=L[0]
        at=L[1]
        k=at.keys()
        print("{:<10} {:<10}".format('DATE','ATTENDANCE'))
        for x in k:
            d=x
            a=at[x]
            print("{:<10} {:<10}".format(d,a))

    attendance_of_particular_student()

def read():
    cn=input("Enter name of the class:")
    nc=cn+".dat"
    f8=open(nc,'rb')
    st = pickle.load(f8)
    print("Content of the File ",cn,'\n')
    k = st.keys()
    for a in k:
        l = st[a]
        nm = l[0]
        atd = l[1]
        print("Admn No: ",a)
        print("Name: ",nm)
        print("Attendance \n",atd,'\n')

read()
    
