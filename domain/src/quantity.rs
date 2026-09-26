#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Quantity(f64);

impl Quantity {
    pub(crate) fn new(value: f64) -> Self {
        Self(value)
    }

    pub fn value(self) -> f64 {
        self.0
    }
}
