import numpy as np
import pandas as pd

from budget.models import Transaction


MAX_ROWS = 120


def one_year_summary(user, class_field=None):
    """Generates a DataFrame summarizing the last 13 months."""
    li = Transaction.objects.in_last_thirteen_months(user)
    if not li.exists():
        return pd.DataFrame()

    # Build DataFrame from query set
    if class_field is None:  # All
        df = pd.DataFrame([
            {'date': t.date,
             'amount': t.amount,
             'class_field': t.class_field.name}
            for t in li
        ])
    else:
        df = pd.DataFrame([
            {'date': t.date,
             'amount': t.amount,
             'category': t.category.name}
            for t in li.filter(pattern__category__class_field=class_field)
        ])

    if df.empty:
        return df

    # Add datetime columns for grouping
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year

    # Pivot
    index = 'class_field' if class_field is None else 'category'
    pivot = pd.pivot_table(df, values='amount', index=index,
                           columns=['year', 'month'], aggfunc=np.sum)
    pivot = pivot.fillna(0)

    # Add total row
    pivot.loc['Total', :] = pivot.sum()

    return pivot
