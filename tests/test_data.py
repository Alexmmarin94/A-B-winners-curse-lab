"""Whole-experiment exclusions, risk boundaries, schemas, and outcome-blind pairing."""
import pandas as pd
import pytest
from src.data.upworthy import clean_partition, load_archive, paired_observations, partition_overlaps


def frame(dates=('2014-02-01', '2014-02-02')):
    return pd.DataFrame({'clickability_test_id':['e']*len(dates), 'package_id':[str(i) for i in range(len(dates))],
        'created_at':dates,'impressions':['1000']*len(dates),'clicks':['20']*len(dates)})


@pytest.mark.parametrize('date,retained', [('2013-06-24 23:59:59',True),('2013-06-25 00:00:00',False),
    ('2014-01-10 23:59:59.999999',False),('2014-01-11 00:00:00',True)])
def test_date_boundaries_exclude_whole_experiment(date,retained):
    result=clean_partition(frame((date,'2014-03-01')), 'exploratory')
    assert (len(result.clean)==2)==retained
    assert result.report['experiments_excluded']==int(not retained)


def test_flags_union_dates_and_invalid_flags():
    f=frame(); f['problem']=['1','0']
    result=clean_partition(f,'exploratory')
    assert result.clean.empty
    assert result.report['flag_date_disagreement_rows']==1
    f['problem']=['0','unknown']
    assert clean_partition(f,'exploratory').clean.empty
    f=frame(('2013-07-01','2013-07-02')); f['problem']=['0','0']
    assert clean_partition(f,'exploratory').clean.empty


@pytest.mark.parametrize('column,value', [('clicks','1001'),('clicks','-1'),('clicks','1.5'),
    ('impressions','0'),('impressions','NaN'),('created_at','invalid'),('package_id',None)])
def test_invalid_row_quarantines_whole_experiment(column,value):
    f=frame(); f.loc[0,column]=value
    assert clean_partition(f,'exploratory').clean.empty


def test_duplicates_missing_ids_and_undeployed():
    f=frame(); f.loc[1,'package_id']='0'
    assert clean_partition(f,'exploratory').clean.empty
    f=frame(); f.loc[0,'clickability_test_id']=None
    result=clean_partition(f,'exploratory')
    assert result.clean.empty
    assert result.report['missing_id_rows']==1
    assert clean_partition(frame(),'undeployed').clean.empty
    assert partition_overlaps({'a':frame(),'b':frame()})=={'a / b':1}


def test_schema_and_pairing_do_not_depend_on_outcomes(tmp_path):
    path=tmp_path/'bad.csv'; pd.DataFrame({'clicks':[2]}).to_csv(path,index=False)
    with pytest.raises(ValueError,match='required'):
        load_archive(path)
    f=frame(('2014-02-01',)*5); f['impressions']=['1000','2000','3000','4000','5000']
    first=paired_observations(clean_partition(f,'exploratory').clean)
    f['clicks']=['999','1','40','10','2500']
    second=paired_observations(clean_partition(f.sample(frac=1,random_state=2),'exploratory').clean)
    assert first[['nc','nt']].equals(second[['nc','nt']])
    assert not first.log_odds_ratio.equals(second.log_odds_ratio)
