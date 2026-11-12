use metrado_calculo::{sheet_quantity, sheet_total, Dimension};

#[test]
fn decimal_geometry_keeps_half_cent_exact() {
    let dims = vec![
        Dimension::try_new("largo", 0.05).unwrap(),
        Dimension::try_new("ancho", 0.70).unwrap(),
    ];
    assert_eq!(sheet_quantity("m2", dims, 1.0, 1.0, None).unwrap(), 0.035);
}

#[test]
fn total_adds_rounded_details_in_decimal() {
    assert_eq!(sheet_total(&[0.035, 0.035]).unwrap(), 0.08);
    assert_eq!(sheet_total(&[0.1, 0.2, -0.3]).unwrap(), 0.0);
    assert_eq!(sheet_total(&[-0.035, -0.035]).unwrap(), -0.08);
}
