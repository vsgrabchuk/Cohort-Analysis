import pandas as pd
from operator import attrgetter
import seaborn as sns


def get_cohort_analysis(
    df,
    unit_column,
    value_column,
    time_column,
    segments_time_interval,
    metric
):
    '''
    Функция возвращает таблицу для проведения когортного анализа
    
    Parameters
    ----------
    df: pandas.DataFrame
        Исходный df
    unit_column: str
        Название колонки с единицей для когортного анализа (напр.: id пользователя)
    value_column: str
        Название колонки, которая будет использоваться для непосредственного 
        расчёта метрики когортного анализа
    time_colunm: str
        Название колонки с временными отсчётами
    segments_time_interval: list(str, str)
        Временной интервал для фильтрации сегментов
    metric: str
        Название метрики, которую необходимо посчитать по когортам
        'retention'
    
    Returns
    -------
    cohorts_df: pandas.DataFrame
        Сводная таблица для выполнения когортного анализа
    '''
    # Добавление столбца с временными периодами
    df['period'] = (
        df[time_column]
        .dt.to_period('M')
    )
    # Добавление столбца соответствия единицы когортного анализа и сегмента
    segmment_compliance = ( 
        df
        .groupby(unit_column, as_index=False)
        .period.min()
        .rename(columns={'period': 'segment'})
    )
    # Добавление информации о сегментах в исходный df
    df = (
        df
        .merge(segmment_compliance, on=unit_column)
    )
    # Фильтрация сегментов
    segment_start = segments_time_interval[0]  # Начало
    segment_fin =   segments_time_interval[1]  # Конец
    df = (
        df
        .query('segment >= @segment_start and segment <= @segment_fin')
    )
    # Добавление столбца с относительными временными единицами
    df = df.assign(
        relative_period=(df.period - df.segment).apply(attrgetter('n'))
    )
    
    # Ветвление в зависимости от необходимой метрики
    if metric == 'retention':
        # Когорты
        cohorts_df = (
            df
            .groupby(['segment', 'relative_period'], as_index=False)
            [unit_column].nunique()
            .rename(columns={unit_column: 'uniqs',
                             'relative_period': 'dt'})
        )
        # uniqs в сегментообразующий период
        period_0_uniqs = (
            cohorts_df
            .groupby(['segment'], as_index=False)
            .uniqs.max()
            .rename(columns={'uniqs': 'period_0_uniqs'})
        )
        # df для расчёта retention
        cohorts_df = (
            cohorts_df
            .merge(period_0_uniqs, on='segment')
        )
        # Расчёт retention
        cohorts_df['metric'] = (
            cohorts_df.uniqs / cohorts_df.period_0_uniqs
            * 100
        )
         
    # Сводная таблица
    cohorts_df = (
        cohorts_df
        .pivot(index='segment', columns='dt', values='metric')
    )
    # heatmap
    cm = sns.color_palette("magma", as_cmap=True)
    cohorts_df = (
        cohorts_df
        .style
        .background_gradient(
            cmap=cm,
            axis=None,
            vmax=cohorts_df[1].max()
        )
        .format('{:.2f}')
        .applymap(lambda x: 'color: transparent' if pd.isnull(x) else '')
        .highlight_null('white')
    )
    
    return cohorts_df