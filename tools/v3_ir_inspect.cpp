#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Verifier.h"
#include "llvm/IR/CFG.h"
#include "llvm/IR/Operator.h"
#include "llvm/IRReader/IRReader.h"
#include "llvm/TargetParser/Triple.h"
#include "llvm/Support/SourceMgr.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/FormatVariadic.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Support/FileSystem.h"
#include <set>
#include <map>
#include <functional>
#include <sstream>
using namespace llvm;
static std::string ty(Type *T) {std::string s;raw_string_ostream o(s);T->print(o);return s;}
static json::Array attrs(AttributeSet A) {json::Array r;for(auto a:A)r.push_back(a.getAsString());return r;}
static bool allowedType(Type *T) {
 if(T->isVoidTy()||T->isLabelTy())return true;
 if(auto *I=dyn_cast<IntegerType>(T)){unsigned b=I->getBitWidth();return b==1||b==8||b==16||b==32||b==64;}
 if(auto *P=dyn_cast<PointerType>(T))return P->getAddressSpace()==0;
 if(auto *A=dyn_cast<ArrayType>(T))return A->getNumElements()<=4096 && allowedType(A->getElementType());
 return false;
}
static bool equalLayout(Type *T,const DataLayout &A,const DataLayout &B) {
 if(!T->isSized())return true;
 return A.getTypeAllocSize(T)==B.getTypeAllocSize(T) && A.getABITypeAlign(T)==B.getABITypeAlign(T);
}
int main(int argc,char **argv) {
 if(argc<3||argc>5){errs()<<"usage: inspect input.ll canonical.ll [source.ll]\n";return 2;}
 LLVMContext C;SMDiagnostic E;auto M=parseIRFile(argv[1],E,C);
 if(!M){E.print("irsem-v3",errs());return 1;}
 if(verifyModule(*M,&errs()))return 1;
 std::unique_ptr<Module> S;if(argc>=4){S=parseIRFile(argv[3],E,C);if(!S){E.print("source",errs());return 2;}}
 std::string RawTriple=M->getTargetTriple(),RawLayout=M->getDataLayoutStr();
 if(S){if(M->getTargetTriple().empty())M->setTargetTriple(S->getTargetTriple());if(M->getDataLayoutStr().empty())M->setDataLayout(S->getDataLayout());}
 json::Object O;O["inherited_target_triple"]=RawTriple.empty() && bool(S);O["inherited_data_layout"]=RawLayout.empty() && bool(S);O["raw_target_triple"]=RawTriple;O["raw_data_layout"]=RawLayout;O["target_triple"]=M->getTargetTriple();O["data_layout"]=M->getDataLayoutStr();
 Triple T(M->getTargetTriple());O["target_vendor"]=T.getVendorName().str();O["abi_target_key"]=T.getArchName().str()+"/"+T.getOSName().str()+"/"+T.getEnvironmentName().str()+"/"+std::to_string((int)T.getObjectFormat());
 O["globals"]=(int64_t)M->global_size();O["aliases"]=(int64_t)M->alias_size();O["ifuncs"]=(int64_t)M->ifunc_size();O["module_asm"]=!M->getModuleInlineAsm().empty();
 json::Array Fns,MD,Errors,Access;bool PtrCompare=false;std::map<std::string,int64_t> Ops;int64_t Defs=0,Decls=0,Ins=0;bool Cyclic=false,LayoutEqual=true;std::set<Type*> Types;
 for(Function &F:*M){if(F.isDeclaration()){Decls++;continue;}Defs++;
  json::Object J;J["name"]=F.getName().str();J["address_space"]=(int64_t)F.getAddressSpace();J["return_type"]=ty(F.getReturnType());J["vararg"]=F.isVarArg();J["calling_convention"]=(int64_t)F.getCallingConv();J["linkage"]=(int64_t)F.getLinkage();J["visibility"]=(int64_t)F.getVisibility();J["dso_local"]=F.isDSOLocal();J["unnamed_addr"]=(int64_t)F.getUnnamedAddr();
  J["function_attrs"]=attrs(F.getAttributes().getFnAttrs());J["return_attrs"]=attrs(F.getAttributes().getRetAttrs());J["personality"]=F.hasPersonalityFn();J["prefix_data"]=F.hasPrefixData();J["prologue_data"]=F.hasPrologueData();J["gc"]=F.hasGC();J["address_taken"]=F.hasAddressTaken();
  json::Array Params;for(Argument &A:F.args()){json::Object Q;Q["type"]=ty(A.getType());Q["attrs"]=attrs(F.getAttributes().getParamAttrs(A.getArgNo()));Params.push_back(std::move(Q));Types.insert(A.getType());}J["params"]=std::move(Params);Types.insert(F.getReturnType());
  std::set<const BasicBlock*> visiting,seen;
  std::function<bool(const BasicBlock*)> visit=[&](const BasicBlock *B){if(visiting.count(B))return true;if(seen.count(B))return false;visiting.insert(B);for(const BasicBlock *N:successors(B))if(visit(N))return true;visiting.erase(B);seen.insert(B);return false;};
  for(BasicBlock &B:F)if(visit(&B))Cyclic=true;
  std::function<unsigned(Value*,std::set<Value*>&)> roots=[&](Value *V,std::set<Value*> &Stack)->unsigned {
   if(auto *A=dyn_cast<Argument>(V))return A->getArgNo()<16 ? 1U<<A->getArgNo() : 1U<<17;
   if(isa<AllocaInst>(V))return 1U<<16;
   if(Stack.count(V))return 1U<<17;Stack.insert(V);unsigned R=0;
   if(auto *G=dyn_cast<GEPOperator>(V))R=roots(G->getPointerOperand(),Stack);
   else if(auto *B=dyn_cast<BitCastOperator>(V))R=roots(B->getOperand(0),Stack);
   else if(auto *S=dyn_cast<SelectInst>(V))R=roots(S->getTrueValue(),Stack)|roots(S->getFalseValue(),Stack);
   else if(auto *P=dyn_cast<PHINode>(V)){for(Value *W:P->incoming_values())R|=roots(W,Stack);}
   else R=1U<<17;Stack.erase(V);return R;
  };
  for(BasicBlock &B:F)for(Instruction &I:B){Ins++;Ops[I.getOpcodeName()]++;Types.insert(I.getType());for(auto &U:I.operands())Types.insert(U->getType());
   if(auto *A=dyn_cast<AllocaInst>(&I)){Types.insert(A->getAllocatedType());if(!isa<ConstantInt>(A->getArraySize()))Errors.push_back("dynamic alloca");else if(cast<ConstantInt>(A->getArraySize())->getZExtValue()>4096 || M->getDataLayout().getTypeAllocSize(A->getAllocatedType()).getFixedValue()*cast<ConstantInt>(A->getArraySize())->getZExtValue()>65536)Errors.push_back("large alloca");}
   if(auto *G=dyn_cast<GetElementPtrInst>(&I))Types.insert(G->getSourceElementType());
   if(auto *L=dyn_cast<LoadInst>(&I))if(L->isVolatile()||L->isAtomic())Errors.push_back("volatile or atomic load");
   if(auto *St=dyn_cast<StoreInst>(&I))if(St->isVolatile()||St->isAtomic())Errors.push_back("volatile or atomic store");
   if(auto *L=dyn_cast<LoadInst>(&I)){std::set<Value*> S;Access.push_back(json::Object{{"op","load"},{"roots",(int64_t)roots(L->getPointerOperand(),S)}});if(!L->getType()->isIntegerTy())Errors.push_back("noninteger memory load");}
   if(auto *St=dyn_cast<StoreInst>(&I)){std::set<Value*> S;Access.push_back(json::Object{{"op","store"},{"roots",(int64_t)roots(St->getPointerOperand(),S)}});if(!St->getValueOperand()->getType()->isIntegerTy())Errors.push_back("noninteger memory store");}
   if(auto *Cmp=dyn_cast<ICmpInst>(&I))if(Cmp->getOperand(0)->getType()->isPointerTy())PtrCompare=true;
   SmallVector<std::pair<unsigned,MDNode*>,8> Mds;I.getAllMetadata(Mds);SmallVector<StringRef,16> Names;C.getMDKindNames(Names);for(auto &P:Mds)MD.push_back(Names[P.first].str());
  }
  Fns.push_back(std::move(J));
 }
 const auto &DL=M->getDataLayout();const auto &SL=S?S->getDataLayout():DL;
 if(S){LayoutEqual=DL.isLittleEndian()==SL.isLittleEndian() && DL.getPointerSizeInBits(0)==SL.getPointerSizeInBits(0) && DL.getIndexSizeInBits(0)==SL.getIndexSizeInBits(0) && DL.getPointerABIAlignment(0)==SL.getPointerABIAlignment(0) && DL.isNonIntegralAddressSpace(0)==SL.isNonIntegralAddressSpace(0);}
 auto component=[](const std::string &L,const std::string &P){std::istringstream Stream(L);std::string X;while(std::getline(Stream,X,'-'))if(X.rfind(P,0)==0)return X;return std::string();};
 if(S){auto AM=component(M->getDataLayoutStr(),"m:");auto BM=component(S->getDataLayoutStr(),"m:");if(AM.empty())AM="m:e";if(BM.empty())BM="m:e";LayoutEqual=LayoutEqual && AM==BM && component(M->getDataLayoutStr(),"S")==component(S->getDataLayoutStr(),"S");}
 json::Array Ts;for(Type *Y:Types){if(!allowedType(Y))Errors.push_back("unsupported type: "+ty(Y));if(S && !equalLayout(Y,DL,SL))LayoutEqual=false;Ts.push_back(ty(Y));}
 json::Array Named;for(NamedMDNode &N:M->named_metadata())Named.push_back(N.getName().str());
 json::Array Flags;SmallVector<Module::ModuleFlagEntry,8> MF;M->getModuleFlagsMetadata(MF);for(auto &F:MF){json::Object A;A["name"]=F.Key->getString().str();A["behavior"]=(int64_t)F.Behavior;if(auto *K=mdconst::dyn_extract<ConstantInt>(F.Val))A["value"]=K->getSExtValue();else A["value_kind"]="noninteger";Flags.push_back(std::move(A));}
 O["memory_accesses"]=std::move(Access);O["pointer_compare"]=PtrCompare;O["functions"]=std::move(Fns);O["definitions"]=Defs;O["declarations"]=Decls;O["instructions"]=Ins;json::Object OP;for(auto &P:Ops)OP[P.first]=P.second;O["opcodes"]=std::move(OP);O["instruction_metadata"]=std::move(MD);O["named_metadata"]=std::move(Named);O["module_flags"]=std::move(Flags);O["scope_errors"]=std::move(Errors);O["cycles"]=Cyclic;O["used_types"]=std::move(Ts);O["layout_equivalent_for_used_types"]=LayoutEqual;
 if(argc==5){
  if(std::string(argv[4])!="--normalize-equivalent-target" || !S){errs()<<"invalid normalization option";return 2;}
  Triple U(S->getTargetTriple());auto V=T.getVendorName();auto W=U.getVendorName();
  bool VendorOK=V==W || ((V=="pc"||V=="unknown")&&(W=="pc"||W=="unknown"));
  if(!LayoutEqual || !VendorOK || T.getArch()!=U.getArch() || T.getOS()!=U.getOS() || T.getEnvironment()!=U.getEnvironment() || T.getObjectFormat()!=U.getObjectFormat()) {errs()<<"target equivalence not established";return 2;}
  O["equivalent_triple_canonicalized"]=M->getTargetTriple()!=S->getTargetTriple();O["equivalent_layout_canonicalized"]=M->getDataLayoutStr()!=S->getDataLayoutStr();
  M->setTargetTriple(S->getTargetTriple());M->setDataLayout(S->getDataLayout());
 }
 std::error_code EC;raw_fd_ostream Out(argv[2],EC,sys::fs::OF_Text);if(EC){errs()<<EC.message();return 2;}M->print(Out,nullptr);Out.flush();outs()<<formatv("{0:2}\n",json::Value(std::move(O)));return 0;
}
