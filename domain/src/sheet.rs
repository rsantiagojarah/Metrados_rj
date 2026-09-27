use crate::{Dimension, DomainError, Partida, Unit};

/// A detail quantity. Geometry and repetition factors are evaluated only here.
pub fn sheet_quantity(
    unit: &str,
    dimensions: Vec<Dimension>,
    similar: f64,
    repetitions: f64,
    direct: Option<f64>,
) -> Result<f64, DomainError> {
    Dimension::try_new("elementos", similar.abs())?;
    Dimension::try_new("repeticiones", repetitions.abs())?;
    let geometric = match unit {
        "m" => Some(Unit::LinearMeter),
        "m2" => Some(Unit::SquareMeter),
        "m3" => Some(Unit::CubicMeter),
        "kg" | "und" | "mes" | "vje" | "glb" => None,
        _ => return Err(DomainError::UnknownUnit),
    };
    let base = if let Some(value) = direct {
        if !dimensions.is_empty() {
            return Err(DomainError::UnexpectedDimension);
        }
        Dimension::try_new("cantidad", value)?.measure()
    } else if let Some(unit) = geometric {
        Partida::try_new("detalle", unit, dimensions)?
            .quantity()
            .value()
    } else {
        if !dimensions.is_empty() {
            return Err(DomainError::UnexpectedDimension);
        }
        if unit == "kg" {
            return Err(DomainError::MissingDimension);
        }
        1.0
    };
    let result = base * similar * repetitions;
    if !result.is_finite() || result == 0.0 {
        return Err(DomainError::NonPositiveMeasure);
    }
    Ok(result)
}

/// Only quantities from one partida (and therefore one unit) may be summed.
pub fn sheet_total(quantities: &[f64]) -> Result<f64, DomainError> {
    let mut total = 0.0;
    for value in quantities {
        if !value.is_finite() {
            return Err(DomainError::NonPositiveMeasure);
        }
        total += value;
        if !total.is_finite() {
            return Err(DomainError::NonPositiveMeasure);
        }
    }
    Ok(total)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dims(values: &[(&str, f64)]) -> Vec<Dimension> {
        values
            .iter()
            .map(|(name, n)| Dimension::try_new(name, *n).unwrap())
            .collect()
    }

    #[test]
    fn geometry_and_repetitions() {
        assert_eq!(
            sheet_quantity("m", dims(&[("longitud", 80.0)]), 1.0, 1.0, None),
            Ok(80.0)
        );
        assert_eq!(
            sheet_quantity(
                "m2",
                dims(&[("largo", 2.0), ("ancho", 3.0)]),
                2.0,
                3.0,
                None
            ),
            Ok(36.0)
        );
        assert_eq!(
            sheet_quantity(
                "m3",
                dims(&[("largo", 2.0), ("ancho", 3.0), ("alto", 4.0)]),
                2.0,
                3.0,
                None
            ),
            Ok(144.0)
        );
    }

    #[test]
    fn direct_area_weight_and_counts() {
        assert_eq!(
            sheet_quantity("m2", vec![], 1.0, 1.0, Some(837.13)),
            Ok(837.13)
        );
        assert_eq!(sheet_quantity("kg", vec![], 2.0, 3.0, Some(4.0)), Ok(24.0));
        for unit in ["und", "mes", "vje", "glb"] {
            assert_eq!(sheet_quantity(unit, vec![], 1.0, 6.0, None), Ok(6.0));
        }
    }

    #[test]
    fn invalid_inputs_do_not_produce_quantities() {
        for value in [0.0, f64::NAN, f64::INFINITY] {
            assert!(sheet_quantity("und", vec![], value, 1.0, None).is_err());
            assert!(sheet_quantity("und", vec![], 1.0, value, None).is_err());
            assert!(sheet_quantity("kg", vec![], 1.0, 1.0, Some(value)).is_err());
        }
        assert!(sheet_quantity("kg", vec![], 1.0, 1.0, Some(-1.0)).is_err());
        assert_eq!(sheet_quantity("und", vec![], -2.0, 3.0, None), Ok(-6.0));
        assert_eq!(sheet_quantity("und", vec![], -2.0, -3.0, None), Ok(6.0));
        assert!(sheet_quantity("kg", vec![], 1.0, 1.0, None).is_err());
        assert!(sheet_quantity("m2", dims(&[("largo", 2.0)]), 1.0, 1.0, None).is_err());
        assert!(sheet_quantity("otro", vec![], 1.0, 1.0, None).is_err());
        assert!(sheet_quantity("m", dims(&[("longitud", 2.0)]), 1.0, 1.0, Some(4.0)).is_err());
    }

    #[test]
    fn overflow_and_underflow_are_rejected() {
        assert!(sheet_quantity("und", vec![], f64::MAX, 2.0, None).is_err());
        assert!(sheet_quantity("und", vec![], f64::MIN_POSITIVE, f64::MIN_POSITIVE, None).is_err());
        assert!(sheet_total(&[f64::MAX, f64::MAX]).is_err());
    }

    #[test]
    fn totals() {
        assert_eq!(sheet_total(&[]), Ok(0.0));
        assert_eq!(sheet_total(&[80.0, 20.0]), Ok(100.0));
        assert!(sheet_total(&[f64::NAN]).is_err());
        assert_eq!(sheet_total(&[10.0, -10.0, 0.0]), Ok(0.0));
        assert_eq!(sheet_total(&[-1.0]), Ok(-1.0));
    }
}
