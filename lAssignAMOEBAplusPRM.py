
#===================================
#        Chengwen Liu              #
#        Xudong Yang               #
#      liuchw2010@gmail.com        #
#      yang2076@utexas.edu         #    
#   University of Texas at Austin  #
#===================================

import sys
import argparse
import numpy as np
from pybel import *
from valenceModule.fitting import *
from valenceModule.typing_tree import *
from valenceModule.typing_tree_assign import *
from valenceModule.modified_Seminario import *

# color
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
ENDC = '\033[0m'

def genAtomType(txyz, key, potent):
  fname, _ = os.path.splitext(txyz)
  lines = open(txyz).readlines()
  if len(lines[0].split()) == 1:
    with open(txyz, "w") as f:
      f.write(lines[0].split("\n")[0] + " comments\n")
      for i in range(1,len(lines)):
        f.write(lines[i])
  atomnumbers, types = np.loadtxt(txyz, usecols=(0, 5,), unpack=True, dtype="str", skiprows=1)
  type_class_dict = {}
  atom_class_dict = {}
  for line in open(key).readlines():
    if "atom " in line:
      d = line.split()
      if d[1] in types:
        type_class_dict[d[1]] = d[2]
  for a,t in zip(atomnumbers, types):
    atom_class_dict[a] = type_class_dict[t]
  for mol in readfile('txyz',txyz):
    matchDict = {}
    matchList = []
    commentsDict = {} 
    classesDict = {} 
    natoms = len(mol.atoms)
    for i in range(1, natoms+1, 1):
      matchList.append(i)
    matchDict = dict.fromkeys(matchList, 0)
    commentsDict = dict.fromkeys(matchList, 0)
    classesDict = dict.fromkeys(matchList, 0)
    potent_typefile_dict = {    "CF": "amoebaplusCFluxType.dat",  \
                             "POLAR": "amoebaplusPolarType.dat",  \
                            "BONDED": "amoebaplusBondedType.dat", \
                         "NONBONDED": "amoebaplusNonbondedType.dat"}
    lines = open(os.path.join(datfiledir, potent_typefile_dict[potent])).readlines()
    for line in lines:
      if ("#" not in line[0]) and (len(line) > 10):
        data = line.split()
        myStr = data[0]
        classNum = data[2]
        className = line.split("# ")[0].split()[-1] 
        comment = line.split("# ")[1][0:-1]
        smarts = Smarts(myStr)
        match = smarts.findall(mol)
        if match:
          for i in range(len(match)):
            matchDict[match[i][0]] = className
            commentsDict[match[i][0]] = comment
            classesDict[match[i][0]] = classNum
    with open(f"{fname}.type.{potent.lower()}", "w") as f:
      for atom in range(1, natoms+1, 1):
        atomtype = types[atom-1]
        atomclass = type_class_dict[atomtype]
        f.write("%5s %5s %5s %5s %5s #%s\n"%(atom, atomtype, atomclass, matchDict[atom], classesDict[atom], commentsDict[atom]))
    if(potent == "CF"):
      lines = open(os.path.join(datfiledir, "amoebaplusCFluxType_general.dat")).readlines()
      for line in lines:
        if ("#" not in line[0]) and (len(line) > 10):
          data = line.split()
          myStr = data[0]
          classNum = data[2]
          className = line.split("# ")[0].split()[-1] 
          comment = line.split("# ")[1][0:-1]
          smarts = Smarts(myStr)
          match = smarts.findall(mol)
          if match:
            for i in range(len(match)):
              matchDict[match[i][0]] = className
              commentsDict[match[i][0]] = comment
              classesDict[match[i][0]] = classNum
      with open(f"{fname}.type.cf_gen", "w") as f:
        for atom in range(1, natoms+1, 1):
          atomtype = types[atom-1]
          atomclass = type_class_dict[atomtype]
          f.write("%5s %5s %5s %5s %5s #%s\n"%(atom, atomtype, atomclass, matchDict[atom], classesDict[atom], commentsDict[atom]))
  return atom_class_dict

def assignPolar(fname, tinkerkey):
  types, polars = np.loadtxt(os.path.join(prmfiledir,"polarize.prm"), usecols=(0,1), unpack=True, dtype="str")
  smartspolarDict = dict(zip(types, polars))
  ttypes, stypes = np.loadtxt(f"{fname}.type.polar", usecols=(1,3), unpack=True, dtype="str")
  tinkerpolarDict = {}
  for t,s in zip(ttypes, stypes): 
    if t not in tinkerpolarDict:
      tinkerpolarDict[t] = smartspolarDict[s]
  lines = open(tinkerkey).readlines()
  with open(tinkerkey + "_polar", "w") as f:
    for line in lines:
      if "polarize " in line:
        dd = line.split()
        if dd[1] in ttypes:
          dd[2] = tinkerpolarDict[dd[1]]
          newline = "    ".join(dd) + "\n"
          oldline = "#" + line
          print(GREEN + "polarizability parameter found for %s"%dd[1] + ENDC)
          f.write(oldline)
          f.write(newline)
  return True

def assignNonbonded(fname, tinkerkey):
  types = np.loadtxt(os.path.join(prmfiledir,"nonbonded.prm"), usecols=(0,), unpack=True, dtype="str",skiprows=2)
  cpalphas, cpnucs = np.loadtxt(os.path.join(prmfiledir,"nonbonded.prm"), usecols=(1,2), unpack=True, dtype="float",skiprows=2)
  ctas, ctbs = np.loadtxt(os.path.join(prmfiledir,"nonbonded.prm"), usecols=(3,4), unpack=True, dtype="float",skiprows=2)
  vdwrs, vdwes, vdwreds = np.loadtxt(os.path.join(prmfiledir,"nonbonded.prm"), usecols=(5,6,7), unpack=True, dtype="float",skiprows=2)
  CP = [[i,j] for i,j in zip(cpalphas, cpnucs)]
  CT = [[i,j] for i,j in zip(ctas, ctbs)]
  VDW = [[i,j,k] for i,j,k in zip(vdwrs, vdwes, vdwreds)]
  smartsCPDict = dict(zip(types, CP))
  smartsCTDict = dict(zip(types, CT))
  smartsVDWDict = dict(zip(types, VDW))
  # !!! attention, vdw/cp/ct may use atom type/atom class, depending on the tinker code
  # it's correct if atom type == atom class, which is the case for a new molecule derived by poltype
  ttypes, stypes = np.loadtxt(f"{fname}.type.nonbonded", usecols=(2,3), unpack=True, dtype="str")
  tinkerCPDict = {}
  tinkerCTDict = {}
  tinkerVDWDict = {}
  for t,s in zip(ttypes, stypes): 
    if t not in tinkerCPDict:
      tinkerCPDict[t] = smartsCPDict[s]
      tinkerCTDict[t] = smartsCTDict[s]
      tinkerVDWDict[t] = smartsVDWDict[s]
  lines = open(tinkerkey).readlines()
  with open(tinkerkey, "a") as f:
    f.write("# charge penetration parameters assigned from database\n")
    for t in tinkerCPDict:
      ''' the commented out line is for old tinker 8.2 '''
      #line = "cp  %5s%10.5f%10.5f\n"%(t, tinkerCPDict[t][0], tinkerCPDict[t][1])
      line = "chgpen  %5s%10.5f%10.5f\n"%(t, tinkerCPDict[t][1], tinkerCPDict[t][0])
      f.write(line)
    print(GREEN + "charge penetration parameters assigned from database"+ ENDC)
    f.write("# charge transfer parameters assigned from database\n")
    for t in tinkerCTDict:
      #line = "ct  %5s%10.5f%10.5f\n"%(t, tinkerCTDict[t][0], tinkerCTDict[t][1])
      line = "chgtrn  %5s%10.5f%10.5f\n"%(t, tinkerCTDict[t][0]*3.01147, tinkerCTDict[t][1])
      f.write(line)
    print(GREEN + "charge transfer parameters assigned from database" + ENDC)
    f.write("# van der Waals parameters assigned from database\n")
    for t in tinkerVDWDict:
      if tinkerVDWDict[t][2] != 1.0:
        line = "vdw  %5s%10.5f%10.5f%10.5f\n"%(t, tinkerVDWDict[t][0], tinkerVDWDict[t][1], tinkerVDWDict[t][2])
      else:
        line = "vdw  %5s%10.5f%10.5f\n"%(t, tinkerVDWDict[t][0], tinkerVDWDict[t][1])
      f.write(line)
    print(GREEN+"van der Waals parameters assigned from database"+ENDC)
  return True

def assignCFlux_general(fname, tinkerkey):
  # read in atom classes and short types (stype) 
  classs, stypes = np.loadtxt(f"{fname}.type.cf_gen", usecols=(2,3), unpack=True, dtype="str")
  class2stype = dict(zip(classs, stypes))
  
  # read in the database CFlux parameters
  # store two sets of parameters
  lines = open(os.path.join(prmfiledir,"cflux2022_general.prm")).readlines()
  stype2param = {}
  for line in lines:
    s = line.split()
    #bndcflux
    if len(s) == 2: 
      key0, value0 = s[0], f"{float(s[1]):10.5f}"
      k = key0.split("_")
      key1 = '_'.join([k[1], k[0]])
      value1 = "%10.5f"%(-float(s[1]))
      stype2param[key0] = value0
      stype2param[key1] = value1
    #angcflux
    if len(s) == 5: 
      key0, value0 = s[0], f"{float(s[1]):10.5f}{float(s[2]):10.5f}{float(s[3]):10.5f}{float(s[4]):10.5f}"
      k = key0.split("_")
      key1 = '_'.join([k[2], k[1], k[0]])
      value1 = f"{float(s[2]):10.5f}{float(s[1]):10.5f}{float(s[4]):10.5f}{float(s[3]):10.5f}"
      stype2param[key0] = value0
      stype2param[key1] = value1
  
  # assign parameters 
  lines = open(tinkerkey).readlines()
  with open(tinkerkey + "_cf","w") as f:
    for line in lines:
      if "bond " in line:
        d = line.split()
        if set(d[1:3]).issubset(set(classs)):
          s1 = class2stype[d[1]]
          s2 = class2stype[d[2]]
          comb = s1 + "_" + s2
          if comb in stype2param:
            f.write("bndcflux %s %s %s\n"%(d[1], d[2], stype2param[comb]))
            print(GREEN + "CFlux parameter assigned for bond %s-%s"%(d[1], d[2]) + ENDC)
          else:
            print(RED + f"CFlux parameter NOT found for bond %s-%s with type {comb}"%(d[1], d[2]) + ENDC)
            
            # do an average 
            jb = []
            s1_ = s1[0] + 'other'
            s2_ = s2[0] + 'other'
            if ("Cl" in s1[:2]) or ("Br" in s1[:2]):
              s1_ = s1[0:2] + 'other'
            if ("Cl" in s2[:2]) or ("Br" in s2[:2]):
              s2_ = s2[0:2] + 'other'
            for n1 in [s1, s1_]:
              for n2 in [s2, s2_]:
                combn = f"{n1}_{n2}"
                if (combn in stype2param):
                  p = stype2param[combn].split()
                  jb.append(float(p[0]))
            jb = "%10.5f"%np.array(jb).mean()
            f.write("bndcflux %s %s %s\n"%(d[1], d[2], jb))
            print(YELLOW + f"CFlux parameter GENERATED for bond %s-%s"%(d[1], d[2]) + ENDC)
      
      if ("angle " in line) or ("anglep " in line):
        d = line.split()
        if set(d[1:4]).issubset(set(classs)):
          s1 = class2stype[d[1]]
          s2 = class2stype[d[2]]
          s3 = class2stype[d[3]]
          if int(d[1]) > int(d[3]):
            s1, s3 = s3, s1
            d[1], d[3] = d[3], d[1]
          comb = f"{s1}_{s2}_{s3}"
          if comb in stype2param:
            f.write("angcflux %s %s %s %s\n"%(d[1], d[2], d[3], stype2param[comb]))
            print(GREEN + "CFlux parameter assigned for angle %s-%s-%s"%(d[1], d[2], d[3]) + ENDC)
          else:
            print(RED + f"CFlux parameter NOT found for angle %s-%s-%s with type {comb}"%(d[1], d[2], d[3]) + ENDC)
            # do an average 
            jt1, jt2, jb1, jb2 = [], [], [], []
            s1_ = s1[0] + 'other'
            s2_ = s2[0] + 'other'
            s3_ = s3[0] + 'other'
            
            if ("Cl" in s1[:2]) or ("Br" in s1[:2]):
              s1_ = s1[0:2] + 'other'
            if ("Cl" in s2[:2]) or ("Br" in s2[:2]):
              s2_ = s2[0:2] + 'other'
            if ("Cl" in s3[:2]) or ("Br" in s3[:2]):
              s3_ = s3[0:2] + 'other'

            for n1 in [s1, s1_]:
              for n2 in [s2, s2_]:
                for n3 in [s3, s3_]:
                  combn = f"{n1}_{n2}_{n3}"
                  if combn in stype2param:
                    p = stype2param[combn].split()
                    jt1.append(float(p[0]))
                    jt2.append(float(p[1]))
                    jb1.append(float(p[2]))
                    jb2.append(float(p[3]))
            if jt1 != []:
              jt1 = "%10.5f"%np.array(jt1).mean()
              jt2 = "%10.5f"%np.array(jt2).mean()
              jb1 = "%10.5f"%np.array(jb1).mean()
              jb2 = "%10.5f"%np.array(jb2).mean()
            else:
              print(RED + "No similar angle found in database. Please assign by yourself" + ENDC)
              f.write("# Please assign the following ZEROS by yourself \n")
              jt1 = '0.0 '
              jt2 = '0.0 '
              jb1 = '0.0 '
              jb2 = '0.0 '
            f.write("angcflux %s %s %s %s\n"%(d[1], d[2], d[3], ''.join([jt1, jt2, jb1, jb2])))
            print(YELLOW + f"CFlux parameter GENERATED for angle %s-%s-%s"%(d[1], d[2], d[3]) + ENDC)
  return True

def assignCFlux(fname, tinkerkey):
  # read in atom classes and short types (stype) 
  atomclasses, databaseclasses = np.loadtxt(f"{fname}.type.cf", usecols=(2,4), unpack=True, dtype="str")
  class2cftype = dict(zip(atomclasses, databaseclasses))
  
  # read in the database CFlux parameters
  # store two sets of parameters
  lines = open(os.path.join(prmfiledir,"cflux2022.prm")).readlines()
  cftype2param = {}
  for line in lines:
    s = line.split()
    #bndcflux
    if len(s) == 4: 
      value0 = f"{float(s[3]):10.4f}"
      k0 = '_'.join([s[1], s[2]])
      value1 = "%10.4f"%(-float(s[3]))
      k1 = '_'.join([s[2], s[1]])
      cftype2param[k0] = value0
      cftype2param[k1] = value1
    #angcflux
    if len(s) == 8: 
      value0 = f"{float(s[4]):10.4f}{float(s[5]):10.4f}{float(s[6]):10.4f}{float(s[7]):10.4f}"
      k0 = '_'.join([s[1], s[2], s[3]])
      value1 = f"{float(s[5]):10.4f}{float(s[4]):10.4f}{float(s[7]):10.4f}{float(s[6]):10.4f}"
      k1 = '_'.join([s[3], s[2], s[1]])
      cftype2param[k0] = value0
      cftype2param[k1] = value1
  
  # assign parameters 
  lines = open(tinkerkey).readlines()
  if_error = False
  with open(tinkerkey + "_cf","w") as f:
    for line in lines:
      if "bond " in line:
        d = line.split()
        if set(d[1:3]).issubset(set(atomclasses)):
          s1 = class2cftype[d[1]]
          s2 = class2cftype[d[2]]
          comb = s1 + "_" + s2
          if comb in cftype2param:
            f.write("bndcflux %s %s %s\n"%(d[1], d[2], cftype2param[comb]))
            print(GREEN + "CFlux parameter assigned for bond %s-%s"%(d[1], d[2]) + ENDC)
          else:
            print(RED + "CFlux parameter NOT found for bond %s-%s"%(d[1], d[2]) + ENDC)
            print(RED + "Try to find CF parameters for this molecule in general CF database")
            if_error = True
            break
      if ("angle " in line) or ("anglep " in line):
        d = line.split()
        if set(d[1:4]).issubset(set(atomclasses)):
          s1 = class2cftype[d[1]]
          s2 = class2cftype[d[2]]
          s3 = class2cftype[d[3]]
          if int(d[1]) > int(d[3]):
            s1, s3 = s3, s1
            d[1], d[3] = d[3], d[1]
          comb = f"{s1}_{s2}_{s3}"
          if comb in cftype2param:
            f.write("angcflux %s %s %s %s\n"%(d[1], d[2], d[3], cftype2param[comb]))
            print(GREEN + "CFlux parameter assigned for angle %s-%s-%s"%(d[1], d[2], d[3]) + ENDC)
          else:
            print(RED + "CFlux parameter NOT found for angle %s-%s-%s"%(d[1], d[2], d[3]) + ENDC)
            print(RED + "Try to find CF parameters for this molecule in general CF database")
            if_error = True
            break
  if(if_error):
    assignCFlux_general(fname, tinkerkey)
  return True

def assignBonded(fname, tinkerkey, new_para_method, fitting = "NO"):
  # 2 methods to generate the new parameters: modified Seminario (Hessian); average by ranking tree (DATABASE)
  # you can choose to fit the new parameters to the given frequencies to improve the accuracy
  atomclasses, databaseclasses = np.loadtxt(f"{fname}.type.bonded", usecols=(2,4), unpack=True, dtype="str")
  tinker2database = dict(zip(atomclasses, databaseclasses))
  fitting_list = []
  para_strings_k = []
  para_strings_kbt = []
  hessian_mat = []
  coords = []

  if(new_para_method == "HESSIAN"):
    bond_list, angle_list, coords, hessian_mat = fchk_info(fname, len(atomclasses))
    eigenvalues, eigenvectors = eigen(len(atomclasses), hessian_mat)
    k_b_dict = bond_projection(bond_list, coords, eigenvalues, eigenvectors, 0.943)
    k_a_dict = bond_projection(angle_list, coords, eigenvalues, eigenvectors, 0.943)
  else:
    tree_1 = typing_tree()
    tree_1.read_ranking_file('typing_tree.log','amoebaplusBondedType.dat')
    tree_1.sorting_tree()

  # bond stretching
  # only assign force constant parameter, since equilibrium length will be from QM
  class1, class2 = np.loadtxt(os.path.join(prmfiledir,"bond.prm"), usecols=(1,2), unpack=True, dtype="str",skiprows=1)
  bondKs, bondLs = np.loadtxt(os.path.join(prmfiledir,"bond.prm"), usecols=(3,4), unpack=True, dtype="float",skiprows=1)
  classes = []
  for c1, c2 in zip(class1, class2):
    classes.append(c1 + "_" + c2)
  classBondParameterDict = dict(zip(classes, zip(bondKs, bondLs)))
  lines = open(tinkerkey).readlines()
  idx = 0
  for line in lines:
    if "ASSIGN" in line:
      idx = lines.index(line)
  with open(tinkerkey) as f:
    for line in lines[idx:]:
      d = line.split()
      if ("bond " in line) and (set(d[1:3]).issubset(set(inclusions))):
        if (d[1] in atomclasses) and (d[2] in atomclasses):
          c1 = tinker2database[d[1]]
          c2 = tinker2database[d[2]]
          comb1 = c1 + "_" + c2
          comb2 = c2 + "_" + c1
          if comb1 in classBondParameterDict:
            para_strings_k.append("bond %s %s %10.4f %s\n"%(d[1], d[2], classBondParameterDict[comb1][0], d[4]))
            para_strings_kbt.append("bond %s %s %10.4f %10.4f\n"%(d[1], d[2], classBondParameterDict[comb1][0], classBondParameterDict[comb1][1]))
            print(GREEN + "BOND stretching parameter assigned for bond %s-%s"%(d[1], d[2]) + ENDC)
          elif comb2 in classBondParameterDict:
            para_strings_k.append("bond %s %s %10.4f %s\n"%(d[1], d[2], classBondParameterDict[comb2][0], d[4]))
            para_strings_kbt.append("bond %s %s %10.4f %10.4f\n"%(d[1], d[2], classBondParameterDict[comb2][0], classBondParameterDict[comb2][1]))
            print(GREEN + "BOND stretching parameter assigned for bond %s-%s"%(d[1], d[2]) + ENDC)
          else:
            is_wild = False
            if(new_para_method == 'DATABASE'):
              _, para, is_wild = typing_tree_assign(tree_1, 'b', comb1, classBondParameterDict)
            else: #HESSIAN
              para = modified_Seminario('b', d[1] + "_" + d[2], atomclasses, k_b_dict)

            if(fitting == 'NO'):
              if(is_wild): 
                para_strings_k.append("# Warning! This bond involves wild type. Please check your structure\n")
              para_strings_k.append("bond %s %s %10.4f %s\n"%(d[1], d[2], para[0], d[4])) # para[0]: k;  para[1]: b 
              para_strings_kbt.append("bond %s %s %10.4f %10.4f\n"%(d[1], d[2], para[0], para[1]))
              print(GREEN + "BOND stretching parameter (newly generated) assigned for bond %s-%s"%(d[1], d[2]) + ENDC)
            else:
              para_strings_k.append("bond %s %s PRM%d_ %s\n"%(d[1], d[2], len(fitting_list), d[4]))
              fitting_list.append(para)

  #angle bending
  class1, class2, class3  = np.loadtxt(os.path.join(prmfiledir, "angle.prm"), usecols=(1, 2, 3), unpack=True, dtype="str",skiprows=1)
  angleKs, angleTs  = np.loadtxt(os.path.join(prmfiledir, "angle.prm"), usecols=(4,5), unpack=True, dtype="float",skiprows=1)
  classes = []
  angKconsts = []
  angThetas = []
  '''store two sets of parameters since angle indices are interchangable''' 
  for c1, c2, c3 in zip(class1, class2, class3):
    classes.append(c1 + "_" + c2 + "_" + c3)
    classes.append(c3 + "_" + c2 + "_" + c1)
  for k,t in zip(angleKs, angleTs):
    angKconsts.append(k)
    angKconsts.append(k)
    angThetas.append(t)
    angThetas.append(t)

  classAngleParameterDict = dict(zip(classes, zip(angKconsts, angThetas)))
  
  with open(tinkerkey) as f:
    for line in lines[idx:]:
      d = line.split()
      if ("angle " in line or "anglep " in line) and (d[1] in inclusions) and (d[2] in inclusions) and (d[3] in inclusions):
        angletype1 = d[1]
        angletype2 = d[2]
        angletype3 = d[3]
        if (angletype1 in atomclasses) and (angletype2 in atomclasses) and (angletype3 in atomclasses):
          c1 = tinker2database[angletype1]
          c2 = tinker2database[angletype2]
          c3 = tinker2database[angletype3]
          comb1 = c1 + "_" + c2 + "_" + c3
          comb2 = c3 + "_" + c2 + "_" + c1
          if (comb1 in classAngleParameterDict):
            para_strings_k.append("%s %s %s %s %10.5f %s\n"%(d[0], angletype1, angletype2, angletype3, classAngleParameterDict[comb1][0], d[5]))
            para_strings_kbt.append("%s %s %s %s %10.5f %10.5f\n"%(d[0], angletype1, angletype2, angletype3, classAngleParameterDict[comb1][0], classAngleParameterDict[comb1][1]))
            print(GREEN + "ANGLE bending parameter found for angle %s-%s-%s"%(angletype1, angletype2, angletype3) + ENDC)
          elif (comb2 in classAngleParameterDict):
            para_strings_k.append("%s %s %s %s %10.5f %s\n"%(d[0], angletype3, angletype2, angletype1, classAngleParameterDict[comb2][0], d[5]))
            para_strings_kbt.append("%s %s %s %s %10.5f %10.5f\n"%(d[0],angletype3, angletype2, angletype1, classAngleParameterDict[comb2][0], classAngleParameterDict[comb2][1]))
            print(GREEN + "ANGLE bending parameter found for angle %s-%s-%s"%(angletype1, angletype2, angletype3) + ENDC)
          else: 
            is_wild = False
            if(new_para_method == 'DATABASE'):
              _, para, is_wild = typing_tree_assign(tree_1, 'a', comb1, classAngleParameterDict)
            else: #'HESSIAN'
              para = modified_Seminario('a', d[1] + "_" + d[2] + "_" + d[3], atomclasses, k_a_dict)

            if(fitting == 'NO'):
              if(is_wild):
                para_strings_k.append("# Warning! This angle involves wild type. Please check your structure\n")
              para_strings_k.append("%s %s %s %s %10.5f %s\n"%(d[0], angletype1, angletype2, angletype3, para[0], d[5]))
              para_strings_kbt.append("%s %s %s %s %10.5f %s\n"%(d[0], angletype1, angletype2, angletype3, para[0], para[1]))
              print(GREEN + "ANGLE bending parameter (newly generated) assigned for angle %s-%s-%s"%(d[1], d[2], d[3]) + ENDC)
            else:
              para_strings_k.append("%s %s %s %s PRM%d_ %s\n"%(d[0], d[1], d[2], d[3], len(fitting_list), d[5]))
              fitting_list.append(para)

  #bond-angle coupling (strbnd term)
  class1, class2, class3  = np.loadtxt(os.path.join(prmfiledir, "strbnd.prm"), usecols=(1, 2, 3), unpack=True, dtype="str",skiprows=1)
  strbndK1, strbndK2  = np.loadtxt(os.path.join(prmfiledir, "strbnd.prm"), usecols=(4,5), unpack=True, dtype="float",skiprows=1)
  classes = []
  strbndKs = []
  '''store two sets of parameters since strbnd is asymetric''' 
  for c1, c2, c3 in zip(class1, class2, class3):
    classes.append(c1 + "_" + c2 + "_" + c3)
    classes.append(c3 + "_" + c2 + "_" + c1)
  for k1, k2 in zip(strbndK1, strbndK2):
    strbndKs.append([k1,k2])
    strbndKs.append([k2,k1])
  classStrbndKconstantDict = dict(zip(classes, strbndKs))
  
  with open(tinkerkey) as f:
    for line in lines[idx:]:
      #if "strbnd " in line:
      # try to find strbnd parameters for every angle
      d = line.split()
      if ("strbnd " in line) and (d[1] in inclusions) and (d[2] in inclusions) and (d[3] in inclusions):
        angletype1 = d[1]
        angletype2 = d[2]
        angletype3 = d[3]
        if (angletype1 in atomclasses) and (angletype2 in atomclasses) and (angletype3 in atomclasses):
          c1 = tinker2database[angletype1]
          c2 = tinker2database[angletype2]
          c3 = tinker2database[angletype3]
          comb1 = c1 + "_" + c2 + "_" + c3
          comb2 = c3 + "_" + c2 + "_" + c1
          if (comb1 in classStrbndKconstantDict):
            tmp = "%10.5f%10.5f"%(classStrbndKconstantDict[comb1][0], classStrbndKconstantDict[comb1][1])
            para_strings_k.append("strbnd %s %s %s %s\n"%(angletype1, angletype2, angletype3, tmp))
            para_strings_kbt.append("strbnd %s %s %s %s\n"%(angletype1, angletype2, angletype3, tmp))
            print(GREEN + "STRBND coupling parameter found for angle %s-%s-%s"%(angletype1, angletype2, angletype3) + ENDC)
          elif (comb2 in classStrbndKconstantDict):
            tmp = "%10.5f%10.5f"%(classStrbndKconstantDict[comb2][0], classStrbndKconstantDict[comb2][1])
            para_strings_k.append("strbnd %s %s %s %s\n"%(angletype3, angletype2, angletype1, tmp))
            para_strings_kbt.append("strbnd %s %s %s %s\n"%(angletype3, angletype2, angletype1, tmp))
            print(GREEN + "STRBND coupling parameter found for angle %s-%s-%s"%(angletype1, angletype2, angletype3) + ENDC)
          else: 
            _, para, is_wild = typing_tree_assign(tree_1, 'ba', comb1, classStrbndKconstantDict)
            if(fitting == 'NO'):
              if(is_wild):
                para_strings_k.append("# Warning! This strbnd involves wild type. Please check your structure\n")
              p0 = "%10.5f"%para[0] 
              p1 = "%10.5f"%para[1] 
              para_strings_k.append("strbnd %s %s %s %s %s\n"%(angletype1, angletype2, angletype3, p0, p1))
              para_strings_kbt.append("strbnd %s %s %s %s %s\n"%(angletype1, angletype2, angletype3, p0, p1))
              print(GREEN + "STRBND coupling parameter (newly generated) assigned for angle %s-%s-%s"%(d[1], d[2], d[3]) + ENDC)
            else:
              para_strings_k.append("strbnd %s %s %s PRM%d_ PRM%d_\n"%(d[1], d[2], d[3], len(fitting_list), len(fitting_list)))
              fitting_list.append(para)

  # out-of-plane bending 
  class1, class2, kopbends = np.loadtxt(os.path.join(prmfiledir,"opbend.prm"), usecols=(1,2,5), unpack=True, dtype="str",skiprows=1)
  classes = []
  for c1, c2 in zip(class1, class2):
    classes.append(c1 + "_" + c2)
  classOpbendKconstantDict = dict(zip(classes, kopbends))
  lines = open(tinkerkey).readlines()
  with open(tinkerkey) as f:
    for line in lines[idx:]:
      d = line.split()
      if ("opbend " in line) and (d[1] in inclusions) and (d[2] in inclusions):
        if (d[1] in atomclasses) and (d[2] in atomclasses):
          c1 = tinker2database[d[1]]
          c2 = tinker2database[d[2]]
          comb = c1 + "_" + c2
          if comb in classOpbendKconstantDict:
            para_strings_k.append("opbend %s %s    0    0 %s\n"%(d[1], d[2], float(classOpbendKconstantDict[comb])))
            para_strings_kbt.append("opbend %s %s    0    0 %s\n"%(d[1], d[2], float(classOpbendKconstantDict[comb])))
            print(GREEN + "OPBEND parameter assigned for bond %s-%s-0-0"%(d[1], d[2]) + ENDC)
          else:
            _, para, is_wild = typing_tree_assign(tree_1, 'o', comb, classOpbendKconstantDict)
            if(is_wild):
              para_strings_k.append("# Warning! This opbend involves wild type. Please check your structure\n")
            para_strings_k.append("opbend %s %s    0    0 %s\n"%(d[1], d[2], para))
            para_strings_kbt.append("opbend %s %s    0    0 %s\n"%(d[1], d[2], para))
            print(GREEN + "OPBEND parameter (newly generated) assigned for bond %s-%s-0-0"%(d[1], d[2]) + ENDC)

  with open(tinkerkey + "_bonded", "w") as f:
    if konly == "YES":
      for line in para_strings_k:
        f.write(line)
    else:
      for line in para_strings_kbt:
        f.write(line)
      
  if(fitting == 'YES'):
    with open("p0.txt", "w") as f:
      for line in fitting_list:
        f.write(line)
    fitting(fname)
  return True
 
def main():
  if len(sys.argv) == 1:
    sys.exit(RED + "please use '-h' option to see usage" + ENDC)
  parser = argparse.ArgumentParser()
  parser.add_argument('-xyz', dest = 'xyz', help = "tinker xyz file", required=True)  
  parser.add_argument('-key', dest = 'key', help = "tinker prm file", required=True)  
  parser.add_argument('-potent', dest = 'potent', help = "potential energy term", required=True, type=str.upper, choices=["POLAR", "CF", "BONDED", "NONBONDED"])  
  parser.add_argument('-fitting', dest = 'fitting', help = "fit the frequencies if new parameters are needed", default="NO", type=str.upper, choices=["YES", "NO"])
  parser.add_argument('-new_para', dest = 'new_para', help = "method to generate the new valence parameters", default="DATABASE", type=str.upper, choices=["HESSIAN", "DATABASE"])  
  parser.add_argument('-konly', dest = 'konly', help = "assign force constant only for valence parameters", default="YES", type=str.upper, choices=["YES", "NO"])  
  parser.add_argument('-atoms', dest = 'atoms', nargs='+', help = "only assign parameters involving these atoms", default = [])  
  args = vars(parser.parse_args())
  xyz = args["xyz"]
  key = args["key"]
  potent = args["potent"]
  new_para = args["new_para"]
  fitting = args["fitting"]
  atoms = args["atoms"]
  global konly
  konly = args["konly"]
  global prmfiledir, datfiledir
  rootdir = os.path.join(os.path.split(__file__)[0])
  prmfiledir = os.path.join(rootdir, 'prm')
  datfiledir = os.path.join(rootdir, 'dat')

  global inclusions
  inclusions = []
  typefile = xyz.split('.')[0] + '.type'
  atom_class = genAtomType(xyz, key, potent)
  if atoms == []:
    inclusions = atom_class.values()
  else:
    inclusions = [atom_class[a] for a in atoms]
  fname, _ = os.path.splitext(xyz)
  if (potent == "POLAR"):
    assignPolar(fname, key)
  elif (potent == "CF"):
    assignCFlux(fname, key) 
  elif (potent == "BONDED"):
    assignBonded(fname, key, new_para, fitting)
  elif (potent == "NONBONDED"):
    assignNonbonded(fname, key) 
  else:
    print(RED + f"{potent} term not supported!" + ENDC)
  return

if __name__ == "__main__":
  main()
